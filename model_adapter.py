"""
模型适配器模块 - 多模型统一接口
支持GLM5、Claude、GPT-4等多种模型
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List
import os
import json
import asyncio
import aiohttp
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BaseModelAdapter(ABC):
    """模型适配器基类"""
    
    def __init__(self, model_id: str, api_key: str):
        self.model_id = model_id
        self.api_key = api_key
        self.request_count = 0
        self.error_count = 0
        self.last_error = None
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict:
        """生成响应"""
        pass
    
    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """计算token数"""
        pass
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "model_id": self.model_id,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1),
            "last_error": self.last_error
        }


class GLM5Adapter(BaseModelAdapter):
    """GLM5模型适配器"""
    
    def __init__(self, model_id: str, api_key: str):
        super().__init__(model_id, api_key)
        self.endpoint = "https://open.bigmodel.cn/api/paas/v3/model-api"
        self.max_retries = 3
        self.timeout = 30
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict:
        """调用GLM5 API，带重试机制"""
        self.request_count += 1
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_id,
            "messages": kwargs.get("messages", [{"role": "user", "content": prompt}]),
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # 添加系统提示词
        if "system_prompt" in kwargs:
            data["messages"].insert(0, {
                "role": "system",
                "content": kwargs["system_prompt"]
            })
        
        # 重试机制
        for attempt in range(self.max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    url = f"{self.endpoint}/{self.model_id}/invoke"
                    logger.info(f"GLM5 API调用 (尝试 {attempt + 1}/{self.max_retries}): {url}")
                    
                    async with session.post(
                        url,
                        headers=headers,
                        json=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            # 解析响应
                            if "choices" in result and len(result["choices"]) > 0:
                                content = result["choices"][0]["message"]["content"]
                                usage = result.get("usage", {})
                                
                                logger.info(f"GLM5调用成功: tokens={usage}")
                                
                                return {
                                    "success": True,
                                    "content": content,
                                    "usage": usage,
                                    "model": self.model_id,
                                    "provider": "zhipu"
                                }
                            else:
                                raise ValueError(f"无效的响应格式: {result}")
                        else:
                            error_text = await response.text()
                            raise Exception(f"API错误 {response.status}: {error_text}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"GLM5超时 (尝试 {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    self.error_count += 1
                    self.last_error = "请求超时"
                    return {
                        "success": False,
                        "error": "请求超时，请稍后重试",
                        "model": self.model_id
                    }
                await asyncio.sleep(2 ** attempt)  # 指数退避
                
            except aiohttp.ClientError as e:
                logger.error(f"GLM5网络错误: {e}")
                if attempt == self.max_retries - 1:
                    self.error_count += 1
                    self.last_error = str(e)
                    return {
                        "success": False,
                        "error": f"网络错误: {str(e)}",
                        "model": self.model_id
                    }
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                logger.error(f"GLM5未知错误: {e}", exc_info=True)
                self.error_count += 1
                self.last_error = str(e)
                return {
                    "success": False,
                    "error": f"未知错误: {str(e)}",
                    "model": self.model_id
                }
    
    async def count_tokens(self, text: str) -> int:
        """估算token数（中文约1.5字/token）"""
        # 混合文本估算
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_chars = len(text) - chinese_chars
        
        # 中文：约1.5字符/token，英文：约4字符/token
        tokens = int(chinese_chars / 1.5) + int(english_chars / 4)
        
        return max(tokens, 1)
    
    async def stream_generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ):
        """流式生成（异步生成器）"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.endpoint}/{self.model_id}/invoke",
                    headers=headers,
                    json=data
                ) as response:
                    async for line in response.content:
                        if line:
                            yield line.decode('utf-8')
        except Exception as e:
            logger.error(f"流式生成错误: {e}")
            yield f"Error: {str(e)}"


class ClaudeAdapter(BaseModelAdapter):
    """Claude模型适配器"""
    
    def __init__(self, model_id: str, api_key: str):
        super().__init__(model_id, api_key)
        self.endpoint = "https://api.anthropic.com/v1/messages"
        self.max_retries = 3
        self.timeout = 30
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict:
        """调用Claude API，带重试机制"""
        self.request_count += 1
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        messages = kwargs.get("messages", [{"role": "user", "content": prompt}])
        
        data = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # 添加系统提示词
        if "system_prompt" in kwargs:
            data["system"] = kwargs["system_prompt"]
        
        # 重试机制
        for attempt in range(self.max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    logger.info(f"Claude API调用 (尝试 {attempt + 1}/{self.max_retries})")
                    
                    async with session.post(
                        self.endpoint,
                        headers=headers,
                        json=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            if "content" in result and len(result["content"]) > 0:
                                content = result["content"][0]["text"]
                                usage = result.get("usage", {})
                                
                                logger.info(f"Claude调用成功: tokens={usage}")
                                
                                return {
                                    "success": True,
                                    "content": content,
                                    "usage": usage,
                                    "model": self.model_id,
                                    "provider": "anthropic"
                                }
                            else:
                                raise ValueError(f"无效的响应格式: {result}")
                        else:
                            error_text = await response.text()
                            raise Exception(f"API错误 {response.status}: {error_text}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"Claude超时 (尝试 {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    self.error_count += 1
                    self.last_error = "请求超时"
                    return {
                        "success": False,
                        "error": "请求超时，请稍后重试",
                        "model": self.model_id
                    }
                await asyncio.sleep(2 ** attempt)
                
            except aiohttp.ClientError as e:
                logger.error(f"Claude网络错误: {e}")
                if attempt == self.max_retries - 1:
                    self.error_count += 1
                    self.last_error = str(e)
                    return {
                        "success": False,
                        "error": f"网络错误: {str(e)}",
                        "model": self.model_id
                    }
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                logger.error(f"Claude未知错误: {e}", exc_info=True)
                self.error_count += 1
                self.last_error = str(e)
                return {
                    "success": False,
                    "error": f"未知错误: {str(e)}",
                    "model": self.model_id
                }
    
    async def count_tokens(self, text: str) -> int:
        """使用Claude tokenizer估算（英文约4字符/token）"""
        # 简化版估算
        return int(len(text) / 4)


class GPT4Adapter(BaseModelAdapter):
    """GPT-4模型适配器"""
    
    def __init__(self, model_id: str, api_key: str):
        super().__init__(model_id, api_key)
        self.endpoint = "https://api.openai.com/v1/chat/completions"
        self.max_retries = 3
        self.timeout = 30
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict:
        """调用OpenAI API，带重试机制"""
        self.request_count += 1
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = kwargs.get("messages", [{"role": "user", "content": prompt}])
        
        data = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # 添加系统提示词
        if "system_prompt" in kwargs:
            data["messages"].insert(0, {
                "role": "system",
                "content": kwargs["system_prompt"]
            })
        
        # 重试机制
        for attempt in range(self.max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    logger.info(f"OpenAI API调用 (尝试 {attempt + 1}/{self.max_retries})")
                    
                    async with session.post(
                        self.endpoint,
                        headers=headers,
                        json=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            if "choices" in result and len(result["choices"]) > 0:
                                content = result["choices"][0]["message"]["content"]
                                usage = result.get("usage", {})
                                
                                logger.info(f"OpenAI调用成功: tokens={usage}")
                                
                                return {
                                    "success": True,
                                    "content": content,
                                    "usage": usage,
                                    "model": self.model_id,
                                    "provider": "openai"
                                }
                            else:
                                raise ValueError(f"无效的响应格式: {result}")
                        else:
                            error_text = await response.text()
                            raise Exception(f"API错误 {response.status}: {error_text}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"OpenAI超时 (尝试 {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    self.error_count += 1
                    self.last_error = "请求超时"
                    return {
                        "success": False,
                        "error": "请求超时，请稍后重试",
                        "model": self.model_id
                    }
                await asyncio.sleep(2 ** attempt)
                
            except aiohttp.ClientError as e:
                logger.error(f"OpenAI网络错误: {e}")
                if attempt == self.max_retries - 1:
                    self.error_count += 1
                    self.last_error = str(e)
                    return {
                        "success": False,
                        "error": f"网络错误: {str(e)}",
                        "model": self.model_id
                    }
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                logger.error(f"OpenAI未知错误: {e}", exc_info=True)
                self.error_count += 1
                self.last_error = str(e)
                return {
                    "success": False,
                    "error": f"未知错误: {str(e)}",
                    "model": self.model_id
                }
    
    async def count_tokens(self, text: str) -> int:
        """使用tiktoken估算（简化版）"""
        # 简化版：约4字符/token
        return int(len(text) / 4)


class DeepSeekAdapter(BaseModelAdapter):
    """DeepSeek模型适配器"""
    
    def __init__(self, model_id: str, api_key: str):
        super().__init__(model_id, api_key)
        self.endpoint = "https://api.deepseek.com/v1/chat/completions"
        self.max_retries = 3
        self.timeout = 30
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict:
        """调用DeepSeek API"""
        self.request_count += 1
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = kwargs.get("messages", [{"role": "user", "content": prompt}])
        
        data = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        if "system_prompt" in kwargs:
            data["messages"].insert(0, {
                "role": "system",
                "content": kwargs["system_prompt"]
            })
        
        for attempt in range(self.max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    logger.info(f"DeepSeek API调用 (尝试 {attempt + 1}/{self.max_retries})")
                    
                    async with session.post(
                        self.endpoint,
                        headers=headers,
                        json=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            if "choices" in result and len(result["choices"]) > 0:
                                content = result["choices"][0]["message"]["content"]
                                usage = result.get("usage", {})
                                
                                logger.info(f"DeepSeek调用成功: tokens={usage}")
                                
                                return {
                                    "success": True,
                                    "content": content,
                                    "usage": usage,
                                    "model": self.model_id,
                                    "provider": "deepseek"
                                }
                            else:
                                raise ValueError(f"无效的响应格式: {result}")
                        else:
                            error_text = await response.text()
                            raise Exception(f"API错误 {response.status}: {error_text}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"DeepSeek超时 (尝试 {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    self.error_count += 1
                    self.last_error = "请求超时"
                    return {
                        "success": False,
                        "error": "请求超时，请稍后重试",
                        "model": self.model_id
                    }
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                logger.error(f"DeepSeek错误: {e}", exc_info=True)
                if attempt == self.max_retries - 1:
                    self.error_count += 1
                    self.last_error = str(e)
                    return {
                        "success": False,
                        "error": f"错误: {str(e)}",
                        "model": self.model_id
                    }
                await asyncio.sleep(2 ** attempt)
    
    async def count_tokens(self, text: str) -> int:
        """估算token数"""
        return int(len(text) / 4)


class QwenAdapter(BaseModelAdapter):
    """通义千问模型适配器"""
    
    def __init__(self, model_id: str, api_key: str):
        super().__init__(model_id, api_key)
        self.endpoint = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.max_retries = 3
        self.timeout = 30
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict:
        """调用通义千问API"""
        self.request_count += 1
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_id,
            "input": {
                "messages": kwargs.get("messages", [{"role": "user", "content": prompt}])
            },
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        }
        
        if "system_prompt" in kwargs:
            data["input"]["messages"].insert(0, {
                "role": "system",
                "content": kwargs["system_prompt"]
            })
        
        for attempt in range(self.max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    logger.info(f"Qwen API调用 (尝试 {attempt + 1}/{self.max_retries})")
                    
                    async with session.post(
                        self.endpoint,
                        headers=headers,
                        json=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            if "output" in result and "text" in result["output"]:
                                content = result["output"]["text"]
                                usage = result.get("usage", {})
                                
                                logger.info(f"Qwen调用成功: tokens={usage}")
                                
                                return {
                                    "success": True,
                                    "content": content,
                                    "usage": usage,
                                    "model": self.model_id,
                                    "provider": "alibaba"
                                }
                            else:
                                raise ValueError(f"无效的响应格式: {result}")
                        else:
                            error_text = await response.text()
                            raise Exception(f"API错误 {response.status}: {error_text}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"Qwen超时 (尝试 {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    self.error_count += 1
                    self.last_error = "请求超时"
                    return {
                        "success": False,
                        "error": "请求超时，请稍后重试",
                        "model": self.model_id
                    }
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                logger.error(f"Qwen错误: {e}", exc_info=True)
                if attempt == self.max_retries - 1:
                    self.error_count += 1
                    self.last_error = str(e)
                    return {
                        "success": False,
                        "error": f"错误: {str(e)}",
                        "model": self.model_id
                    }
                await asyncio.sleep(2 ** attempt)
    
    async def count_tokens(self, text: str) -> int:
        """估算token数"""
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5) + int(english_chars / 4)


class ModelAdapter:
    """模型适配器管理"""
    
    def __init__(self, config_path: str = None):
        self.adapters: Dict[str, BaseModelAdapter] = {}
        self.config = self.load_config(config_path)
        self.setup_adapters()
        logger.info(f"ModelAdapter初始化完成，可用模型: {list(self.adapters.keys())}")
    
    def load_config(self, config_path: str) -> Dict:
        """加载配置"""
        # 1. 优先使用指定路径
        if config_path and os.path.exists(config_path):
            logger.info(f"从指定路径加载配置: {config_path}")
            with open(config_path) as f:
                return json.load(f)
        
        # 2. 查找默认配置文件
        config_file = os.path.expanduser("~/.nanobot/config.json")
        if os.path.exists(config_file):
            logger.info(f"从默认路径加载配置: {config_file}")
            with open(config_file) as f:
                return json.load(f)
        
        # 3. 查找项目配置
        project_config = os.path.join(os.getcwd(), "config.json")
        if os.path.exists(project_config):
            logger.info(f"从项目路径加载配置: {project_config}")
            with open(project_config) as f:
                return json.load(f)
        
        logger.warning("未找到配置文件，将从环境变量读取API密钥")
        return {}
    
    def setup_adapters(self):
        """设置适配器"""
        # 模型配置：(model_id, adapter_class, api_key_field)
        models = {
            # GLM5系列
            "glm5-plus": ("glm-5-plus", GLM5Adapter, "zhipu_api_key"),
            "glm5-turbo": ("glm-5-turbo", GLM5Adapter, "zhipu_api_key"),
            "glm5-lite": ("glm-5-lite", GLM5Adapter, "zhipu_api_key"),
            
            # Claude系列
            "claude-3-opus": ("claude-3-opus-20240229", ClaudeAdapter, "anthropic_api_key"),
            "claude-3-sonnet": ("claude-3-sonnet-20240229", ClaudeAdapter, "anthropic_api_key"),
            "claude-3-haiku": ("claude-3-haiku-20240307", ClaudeAdapter, "anthropic_api_key"),
            
            # GPT系列
            "gpt-4-turbo": ("gpt-4-turbo-preview", GPT4Adapter, "openai_api_key"),
            "gpt-4": ("gpt-4", GPT4Adapter, "openai_api_key"),
            "gpt-3.5-turbo": ("gpt-3.5-turbo", GPT4Adapter, "openai_api_key"),
            
            # DeepSeek系列
            "deepseek-chat": ("deepseek-chat", DeepSeekAdapter, "deepseek_api_key"),
            "deepseek-coder": ("deepseek-coder", DeepSeekAdapter, "deepseek_api_key"),
            
            # 通义千问系列
            "qwen-max": ("qwen-max", QwenAdapter, "qwen_api_key"),
            "qwen-plus": ("qwen-plus", QwenAdapter, "qwen_api_key"),
            "qwen-turbo": ("qwen-turbo", QwenAdapter, "qwen_api_key")
        }
        
        for name, (model_id, adapter_class, api_key_field) in models.items():
            # 从配置或环境变量获取API密钥
            api_key = self.config.get(api_key_field) or os.getenv(api_key_field.upper())
            
            if api_key:
                try:
                    self.adapters[name] = adapter_class(model_id, api_key)
                    logger.info(f"成功初始化模型适配器: {name}")
                except Exception as e:
                    logger.error(f"初始化模型适配器失败 {name}: {e}")
            else:
                logger.debug(f"跳过模型 {name}: 未找到API密钥 ({api_key_field})")
    
    async def call_model(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict:
        """调用指定模型"""
        if model not in self.adapters:
            available = list(self.adapters.keys())
            logger.error(f"模型 {model} 不可用，可用模型: {available}")
            return {
                "success": False,
                "error": f"模型 {model} 不可用或未配置",
                "available_models": available
            }
        
        try:
            adapter = self.adapters[model]
            result = await adapter.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return result
        except Exception as e:
            logger.error(f"调用模型 {model} 失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "model": model
            }
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return list(self.adapters.keys())
    
    def get_model_stats(self, model: str) -> Optional[Dict]:
        """获取模型统计信息"""
        if model in self.adapters:
            return self.adapters[model].get_stats()
        return None
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """获取所有模型统计信息"""
        return {
            model: adapter.get_stats()
            for model, adapter in self.adapters.items()
        }
    
    async def count_tokens(self, model: str, text: str) -> int:
        """计算指定模型的token数"""
        if model in self.adapters:
            return await self.adapters[model].count_tokens(text)
        
        # 默认估算
        return int(len(text) / 4)
    
    async def batch_call(
        self,
        requests: List[Dict],
        max_concurrent: int = 5
    ) -> List[Dict]:
        """批量调用模型（并发控制）"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def call_with_semaphore(request: Dict):
            async with semaphore:
                return await self.call_model(**request)
        
        tasks = [call_with_semaphore(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "error": str(result),
                    "request_index": i
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_preferred_model(self, task_type: str = "general") -> Optional[str]:
        """获取推荐模型（优先GLM5）"""
        # 优先级：GLM5 > DeepSeek > 其他
        preferred_order = [
            "glm5-plus", "glm5-turbo", "glm5-lite",
            "deepseek-chat", "deepseek-coder",
            "qwen-max", "qwen-plus",
            "gpt-4-turbo", "gpt-4",
            "claude-3-sonnet", "claude-3-opus"
        ]
        
        for model in preferred_order:
            if model in self.adapters:
                return model
        
        # 如果没有优先模型，返回第一个可用的
        if self.adapters:
            return list(self.adapters.keys())[0]
        
        return None


# 便捷函数
async def quick_call(
    prompt: str,
    model: str = None,
    **kwargs
) -> Dict:
    """快速调用模型"""
    adapter = ModelAdapter()
    
    if model is None:
        model = adapter.get_preferred_model()
    
    if model is None:
        return {
            "success": False,
            "error": "没有可用的模型"
        }
    
    return await adapter.call_model(model, prompt, **kwargs)


if __name__ == "__main__":
    # 测试代码
    async def test():
        adapter = ModelAdapter()
        
        print("可用模型:", adapter.get_available_models())
        
        # 测试调用（需要配置API密钥）
        if adapter.get_available_models():
            model = adapter.get_preferred_model()
            print(f"\n使用模型: {model}")
            
            result = await adapter.call_model(
                model,
                "你好，请介绍一下你自己",
                max_tokens=100
            )
            
            print("\n响应:", result)
    
    asyncio.run(test())
