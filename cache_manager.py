"""
缓存管理器 - 优化系统性能

功能：
1. 分析结果缓存（Code Review、复杂度分析等）
2. LRU缓存策略
3. TTL过期机制
4. 缓存命中率统计
"""

import os
import json
import time
import hashlib
from typing import Dict, Any, Optional
from functools import lru_cache
from pathlib import Path
from datetime import datetime


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: str = None, ttl: int = 3600, max_size: int = 1000):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录
            ttl: 缓存过期时间（秒）
            max_size: 最大缓存数量
        """
        self.cache_dir = cache_dir or os.path.expanduser("~/.nanobot/cache")
        self.ttl = ttl
        self.max_size = max_size
        
        # 内存缓存
        self.memory_cache = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
        
        # 创建缓存目录
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 加载持久化缓存
        self._load_persistent_cache()
    
    def _generate_key(self, data: Any) -> str:
        """生成缓存键"""
        if isinstance(data, str):
            content = data
        else:
            content = json.dumps(data, sort_keys=True)
        
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值（如果存在且未过期）
        """
        # 检查内存缓存
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            
            # 检查是否过期
            if time.time() - entry["timestamp"] > self.ttl:
                del self.memory_cache[key]
                self.cache_stats["misses"] += 1
                return None
            
            # 更新访问时间
            entry["last_access"] = time.time()
            self.cache_stats["hits"] += 1
            return entry["value"]
        
        # 检查持久化缓存
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file) as f:
                    entry = json.load(f)
                
                # 检查是否过期
                if time.time() - entry["timestamp"] > self.ttl:
                    os.remove(cache_file)
                    self.cache_stats["misses"] += 1
                    return None
                
                # 加载到内存缓存
                self.memory_cache[key] = entry
                self.cache_stats["hits"] += 1
                return entry["value"]
            except Exception as e:
                print(f"Error loading cache: {e}")
        
        self.cache_stats["misses"] += 1
        return None
    
    def set(self, key: str, value: Any, persist: bool = False):
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            persist: 是否持久化
        """
        # 检查缓存大小
        if len(self.memory_cache) >= self.max_size:
            self._evict_lru()
        
        entry = {
            "value": value,
            "timestamp": time.time(),
            "last_access": time.time()
        }
        
        # 保存到内存
        self.memory_cache[key] = entry
        
        # 持久化
        if persist:
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            try:
                with open(cache_file, 'w') as f:
                    json.dump(entry, f)
            except Exception as e:
                print(f"Error persisting cache: {e}")
    
    def _evict_lru(self):
        """淘汰最少使用的缓存"""
        if not self.memory_cache:
            return
        
        # 找到最久未使用的键
        lru_key = min(
            self.memory_cache.keys(),
            key=lambda k: self.memory_cache[k]["last_access"]
        )
        
        del self.memory_cache[lru_key]
        self.cache_stats["evictions"] += 1
    
    def _load_persistent_cache(self):
        """加载持久化缓存"""
        if not os.path.exists(self.cache_dir):
            return
        
        # 只加载最近的缓存
        cache_files = sorted(
            Path(self.cache_dir).glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:100]  # 只加载最近的100个
        
        for cache_file in cache_files:
            try:
                with open(cache_file) as f:
                    entry = json.load(f)
                
                # 检查是否过期
                if time.time() - entry["timestamp"] <= self.ttl:
                    key = cache_file.stem
                    self.memory_cache[key] = entry
            except Exception as e:
                print(f"Error loading cache file {cache_file}: {e}")
    
    def clear_expired(self):
        """清理过期缓存"""
        current_time = time.time()
        
        # 清理内存缓存
        expired_keys = [
            k for k, v in self.memory_cache.items()
            if current_time - v["timestamp"] > self.ttl
        ]
        
        for key in expired_keys:
            del self.memory_cache[key]
        
        # 清理持久化缓存
        if os.path.exists(self.cache_dir):
            for cache_file in Path(self.cache_dir).glob("*.json"):
                try:
                    with open(cache_file) as f:
                        entry = json.load(f)
                    
                    if current_time - entry["timestamp"] > self.ttl:
                        os.remove(cache_file)
                except:
                    pass
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (
            self.cache_stats["hits"] / total_requests * 100
            if total_requests > 0
            else 0
        )
        
        return {
            "total_requests": total_requests,
            "hits": self.cache_stats["hits"],
            "misses": self.cache_stats["misses"],
            "evictions": self.cache_stats["evictions"],
            "hit_rate": f"{hit_rate:.2f}%",
            "cache_size": len(self.memory_cache),
            "max_size": self.max_size
        }
    
    # ============ 专用缓存方法 ============
    
    @lru_cache(maxsize=1000)
    def get_code_analysis(self, code_hash: str) -> Optional[Dict]:
        """获取代码分析缓存"""
        return self.get(f"analysis_{code_hash}")
    
    def cache_code_analysis(self, code: str, result: Dict):
        """缓存代码分析结果"""
        code_hash = self._generate_key(code)
        self.set(f"analysis_{code_hash}", result, persist=True)
    
    def get_complexity_analysis(self, description: str) -> Optional[Dict]:
        """获取复杂度分析缓存"""
        key = self._generate_key(f"complexity_{description}")
        return self.get(key)
    
    def cache_complexity_analysis(self, description: str, result: Dict):
        """缓存复杂度分析结果"""
        key = self._generate_key(f"complexity_{description}")
        self.set(key, result, persist=True)
    
    def get_review_result(self, code_hash: str) -> Optional[Dict]:
        """获取Code Review结果缓存"""
        return self.get(f"review_{code_hash}")
    
    def cache_review_result(self, code: str, result: Dict):
        """缓存Code Review结果"""
        code_hash = self._generate_key(code)
        self.set(f"review_{code_hash}", result, persist=True)


# 全局缓存管理器实例
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


# 使用示例
if __name__ == "__main__":
    cache = get_cache_manager()
    
    # 测试缓存
    test_data = {"test": "data"}
    cache.set("test_key", test_data)
    
    result = cache.get("test_key")
    print(f"Cache result: {result}")
    
    # 统计
    stats = cache.get_stats()
    print(f"Cache stats: {stats}")
