"""多提供商 LLM 客户端，支持自动故障转移。

架构：Provider[] → 自动选择可用提供商 → 重试 → 降级到下一个提供商。

配置示例（config.yaml）：
  providers:
    - name: deepseek_direct
      base_url: https://api.deepseek.com/v1
      api_key: sk-xxx
      models:
        extract: deepseek-chat
        generate: deepseek-chat
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field

logger = logging.getLogger("llm_client")


@dataclass
class LLMResponse:
    content: str
    usage: dict = field(default_factory=dict)
    finish_reason: str = ""
    elapsed_seconds: float = 0.0
    provider: str = ""       # 实际使用的提供商名称
    model: str = ""          # 实际使用的模型 ID


@dataclass
class ProviderConfig:
    """单个提供商的配置。"""
    name: str
    base_url: str
    api_key: str
    models: dict[str, str]   # {"extract": "model-id", "generate": "model-id"}
    cost_per_million: float = 0.0
    region: str = "global"

    # 健康检查参数（从配置文件读取）
    fail_threshold: int = 3
    health_window_seconds: float = 300

    # 运行时状态
    _fail_count: int = field(default=0, repr=False)
    _last_fail_time: float = field(default=0.0, repr=False)

    @property
    def is_healthy(self) -> bool:
        if self._fail_count >= self.fail_threshold and (time.time() - self._last_fail_time) < self.health_window_seconds:
            return False
        return True

    def mark_success(self):
        self._fail_count = 0

    def mark_failure(self):
        self._fail_count += 1
        self._last_fail_time = time.time()


class LLMClient:
    """多提供商 LLM 客户端，自动故障转移。"""

    # 触发故障转移的 HTTP 状态码
    FALLBACK_STATUS_CODES = {403, 429, 502, 503, 504}

    def __init__(
        self,
        providers: list[ProviderConfig] | None = None,
        task: str = "extract",       # "extract" or "generate"
        timeout: float = 60.0,
        max_retries: int = 1,
        failover_status_codes: set[int] | None = None,
        retry_delay_seconds: float = 2.0,
        retry_temp_increment: float = 0.05,
        retry_temp_max: float = 0.2,
    ):
        if failover_status_codes:
            self.FALLBACK_STATUS_CODES = failover_status_codes

        self._providers = providers or []
        self._task = task
        # timeout 作为读取超时，连接超时固定 10s
        self._timeout = (10, timeout)
        self._max_retries = max_retries
        self._retry_delay = retry_delay_seconds
        self._retry_temp_increment = retry_temp_increment
        self._retry_temp_max = retry_temp_max

        if not self._providers:
            raise ValueError(
                "未配置任何 LLM 提供商。请检查 config.yaml 中的 providers 配置。\n"
                "支持多个提供商自动故障转移：DeepSeek 直连 / 通义千问 / OpenRouter / 本地 vLLM"
            )

    @classmethod
    def from_config(cls, config_path: str = "config.yaml", task: str = "extract") -> "LLMClient":
        """从 config.yaml 创建客户端，自动加载所有提供商。"""
        import yaml

        providers = []

        # 1. 从 providers 列表加载（新版配置）
        path = os.path.abspath(config_path)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}

            health_cfg = cfg.get("failover", {}).get("health_check", {})
            fail_threshold = health_cfg.get("fail_threshold", 3)
            health_window = health_cfg.get("window_seconds", 300)

            for p_cfg in cfg.get("providers", []):
                api_key = p_cfg.get("api_key", "")
                if not api_key or api_key == "EMPTY" and p_cfg.get("region") != "local":
                    continue  # 跳过未配置 key 的提供商（本地部署除外）

                providers.append(ProviderConfig(
                    name=p_cfg["name"],
                    base_url=p_cfg["base_url"],
                    api_key=api_key,
                    models=p_cfg.get("models", {}),
                    cost_per_million=p_cfg.get("cost_per_million", 0),
                    region=p_cfg.get("region", "global"),
                    fail_threshold=fail_threshold,
                    health_window_seconds=health_window,
                ))

            failover_cfg = cfg.get("failover", {})
            timeout = failover_cfg.get("timeout_seconds", 60)
            max_retries = failover_cfg.get("max_retries_per_provider", 1)
            fallback_codes = set(failover_cfg.get("fallback_on_status_codes", [403, 429, 502, 503]))
            retry_delay = failover_cfg.get("retry_delay_seconds", 2)

            temp_cfg = failover_cfg.get("retry_temperature", {})
            temp_increment = temp_cfg.get("increment", 0.05)
            temp_max = temp_cfg.get("max", 0.2)
        else:
            timeout = 60
            max_retries = 1
            fallback_codes = {403, 429, 502, 503}
            retry_delay = 2
            temp_increment = 0.05
            temp_max = 0.2

        # 2. 兼容旧版单 provider 配置
        if not providers:
            cfg_path = os.path.abspath(config_path)
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                if cfg.get("api_key"):
                    providers.append(ProviderConfig(
                        name="default",
                        base_url=cfg.get("base_url", "https://openrouter.ai/api/v1"),
                        api_key=cfg["api_key"],
                        models={"extract": cfg.get("model", {}).get("extract", "deepseek/deepseek-chat-v3-0324") if isinstance(cfg.get("model"), dict) else cfg.get("model", "deepseek/deepseek-chat-v3-0324")},
                    ))

        return cls(
            providers=providers,
            task=task,
            timeout=timeout,
            max_retries=max_retries,
            failover_status_codes=fallback_codes,
            retry_delay_seconds=retry_delay,
            retry_temp_increment=temp_increment,
            retry_temp_max=temp_max,
        )

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.05,
        max_tokens: int = 4000,
    ) -> LLMResponse:
        """发送聊天请求，自动在提供商之间故障转移。

        策略：按优先级遍历提供商，每个提供商最多重试 max_retries 次。
        如果返回 FALLBACK_STATUS_CODES 中的状态码，跳到下一个提供商。
        """
        import httpx

        errors: list[str] = []

        for provider in self._providers:
            if not provider.is_healthy:
                logger.info(f"[{provider.name}] 跳过（近期失败过多）")
                continue

            model = provider.models.get(self._task, "")
            if not model:
                continue

            logger.info(f"[{provider.name}] 尝试模型 {model}")

            # 同一提供商内重试（提高 temperature）
            temps = [temperature]
            if self._max_retries > 0:
                temps.append(min(temperature + self._retry_temp_increment, self._retry_temp_max))

            for i, temp in enumerate(temps):
                start = time.time()
                try:
                    resp = httpx.post(
                        f"{provider.base_url.rstrip('/')}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {provider.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_message},
                            ],
                            "temperature": temp,
                            "max_tokens": max_tokens,
                        },
                        timeout=self._timeout,
                    )

                    # 检查是否需要故障转移到下一个提供商
                    if resp.status_code in self.FALLBACK_STATUS_CODES:
                        err_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
                        logger.warning(f"[{provider.name}] {err_msg}")
                        provider.mark_failure()
                        errors.append(f"[{provider.name}] {err_msg}")
                        break  # 跳到下一个提供商，不在同一提供商重试

                    resp.raise_for_status()

                    try:
                        data = resp.json()
                    except Exception as json_err:
                        # JSON 解析失败 —— 记录响应片段用于诊断
                        snippet = resp.text[:500] if resp.text else "(empty)"
                        logger.error(
                            f"[{provider.name}] JSON 解析失败: {json_err}\n"
                            f"  HTTP {resp.status_code}, Content-Type: {resp.headers.get('content-type', '?')}\n"
                            f"  响应前500字符: {snippet}"
                        )
                        raise

                    elapsed = time.time() - start

                    choice = data.get("choices", [{}])[0]
                    content = choice.get("message", {}).get("content", "")
                    usage = data.get("usage", {})

                    provider.mark_success()
                    logger.info(f"[{provider.name}] 成功 ({elapsed:.1f}s, {usage.get('total_tokens', 0)} tokens)")

                    return LLMResponse(
                        content=content,
                        usage=usage,
                        finish_reason=choice.get("finish_reason", ""),
                        elapsed_seconds=elapsed,
                        provider=provider.name,
                        model=model,
                    )

                except httpx.HTTPStatusError as e:
                    err_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                    logger.warning(f"[{provider.name}] {err_msg}")
                    provider.mark_failure()
                    errors.append(f"[{provider.name}] {err_msg}")
                    break  # HTTP 错误直接跳到下一个提供商

                except Exception as e:
                    errors.append(f"[{provider.name}] {e}")
                    if i < len(temps) - 1:
                        if self._retry_delay > 0:
                            time.sleep(self._retry_delay)
                        continue  # 超时等临时错误，同一提供商重试

        raise RuntimeError(
            f"所有 LLM 提供商均不可用（共 {len(self._providers)} 个，尝试了 {len(errors)} 次）:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )
