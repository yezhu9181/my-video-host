#!/usr/bin/env python3
"""
测试使用 commit SHA 的 CDN URL 是否能获取最新数据
"""

import json
import requests
import time
from pathlib import Path

def test_cdn_with_commit_sha():
    """测试使用 commit SHA 的 CDN URL"""
    local_file = Path("videos.json")
    cdn_base = "https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host"
    
    print("=" * 60)
    print("测试使用 commit SHA 的 CDN URL")
    print("=" * 60)
    
    # 读取本地文件
    print("\n1. 读取本地 videos.json 文件...")
    if not local_file.exists():
        print("❌ 本地文件不存在")
        return False
    
    with open(local_file, 'r', encoding='utf-8') as f:
        local_data = json.load(f)
    
    local_last_updated = local_data.get('lastUpdated', 'N/A')
    local_cache_version = local_data.get('cacheVersion', 'N/A')
    commit_sha = local_data.get('latestCommitSha', None)
    
    print(f"   ✅ 本地文件读取成功")
    print(f"   - 更新时间: {local_last_updated}")
    print(f"   - 缓存版本: {local_cache_version}")
    print(f"   - Commit SHA: {commit_sha or 'N/A'}")
    
    if not commit_sha:
        print("\n❌ 未找到 commit SHA，无法测试")
        return False
    
    # 测试使用 commit SHA 的 CDN URL
    print(f"\n2. 测试使用 commit SHA 的 CDN URL...")
    
    # 方法1: 使用 @commit_sha
    cdn_url_with_sha = f"{cdn_base}@{commit_sha}/videos.json"
    print(f"\n   方法1: 使用 @commit_sha")
    print(f"   URL: {cdn_url_with_sha}")
    
    try:
        response = requests.get(cdn_url_with_sha, timeout=10)
        if response.status_code == 200:
            cdn_data = response.json()
            cdn_last_updated = cdn_data.get('lastUpdated', 'N/A')
            cdn_cache_version = cdn_data.get('cacheVersion', 'N/A')
            
            print(f"   ✅ 请求成功")
            print(f"   - 更新时间: {cdn_last_updated}")
            print(f"   - 缓存版本: {cdn_cache_version}")
            
            if (cdn_last_updated == local_last_updated and 
                cdn_cache_version == local_cache_version):
                print(f"\n   ✅ 数据一致！使用 commit SHA 的 CDN URL 返回的是最新数据")
                return True
            else:
                print(f"\n   ❌ 数据不一致")
                print(f"      - 本地: {local_last_updated} / {local_cache_version}")
                print(f"      - CDN:  {cdn_last_updated} / {cdn_cache_version}")
        else:
            print(f"   ❌ HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    # 方法2: 使用 @main 作为对比
    print(f"\n   方法2: 使用 @main (对比)")
    cdn_url_main = f"{cdn_base}@main/videos.json"
    print(f"   URL: {cdn_url_main}")
    
    try:
        response = requests.get(cdn_url_main, timeout=10)
        if response.status_code == 200:
            cdn_data = response.json()
            cdn_last_updated = cdn_data.get('lastUpdated', 'N/A')
            cdn_cache_version = cdn_data.get('cacheVersion', 'N/A')
            
            print(f"   ✅ 请求成功")
            print(f"   - 更新时间: {cdn_last_updated}")
            print(f"   - 缓存版本: {cdn_cache_version}")
            
            if (cdn_last_updated == local_last_updated and 
                cdn_cache_version == local_cache_version):
                print(f"\n   ✅ @main 也返回最新数据")
            else:
                print(f"\n   ❌ @main 返回的是旧数据（缓存问题）")
                print(f"      - 本地: {local_last_updated} / {local_cache_version}")
                print(f"      - CDN:  {cdn_last_updated} / {cdn_cache_version}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    return False

if __name__ == "__main__":
    success = test_cdn_with_commit_sha()
    exit(0 if success else 1)

