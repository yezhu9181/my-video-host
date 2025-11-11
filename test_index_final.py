#!/usr/bin/env python3
"""
测试 index.html 的最终逻辑：使用 @main 也能获取最新数据
"""

import json
import requests
import time
from pathlib import Path

def test_index_final():
    """测试使用 @main 的 URL 是否能获取最新数据（通过 index.html 自动替换）"""
    print("=" * 60)
    print("测试 index.html 最终逻辑：使用 @main 也能获取最新数据")
    print("=" * 60)
    
    # 读取本地文件
    local_file = Path("videos.json")
    with open(local_file, 'r', encoding='utf-8') as f:
        local_data = json.load(f)
    
    local_last_updated = local_data.get('lastUpdated')
    local_cache_version = local_data.get('cacheVersion')
    
    print(f"\n1. 本地数据:")
    print(f"   - 更新时间: {local_last_updated}")
    print(f"   - 缓存版本: {local_cache_version}")
    
    # 步骤1: 从 GitHub API 获取 commit SHA（模拟 index.html 内部逻辑）
    print(f"\n2. 步骤1: 从 GitHub API 获取 commit SHA（index.html 内部）...")
    try:
        api_url = 'https://api.github.com/repos/yezhu9181/my-video-host/commits/main'
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            commit_data = response.json()
            commit_sha = commit_data.get('sha')
            
            if commit_sha:
                print(f"   ✅ 获取到 commit SHA: {commit_sha}")
            else:
                print(f"   ❌ GitHub API 返回的数据中没有 commit SHA")
                return False
        else:
            print(f"   ❌ GitHub API 请求失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 获取 commit SHA 失败: {e}")
        return False
    
    # 步骤2: 使用 commit SHA 替换 @main（模拟 index.html 自动替换）
    print(f"\n3. 步骤2: index.html 自动替换 @main 为 commit SHA...")
    
    # 原始 URL（前端配置中的 @main）
    original_url = "https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/videos.json"
    print(f"   原始 URL（前端配置）: {original_url}")
    
    # 替换后的 URL（index.html 自动替换）
    replaced_url = original_url.replace("@main", f"@{commit_sha}")
    print(f"   替换后 URL（index.html 自动替换）: {replaced_url}")
    
    # 步骤3: 使用替换后的 URL 从 CDN 获取数据
    print(f"\n4. 步骤3: 使用替换后的 URL 从 CDN 获取数据...")
    try:
        response = requests.get(replaced_url, timeout=10)
        if response.status_code == 200:
            cdn_data = response.json()
            cdn_last_updated = cdn_data.get('lastUpdated')
            cdn_cache_version = cdn_data.get('cacheVersion')
            
            print(f"   ✅ CDN 请求成功")
            print(f"   - 更新时间: {cdn_last_updated}")
            print(f"   - 缓存版本: {cdn_cache_version}")
            
            # 验证是否是最新数据
            if (cdn_last_updated == local_last_updated and 
                cdn_cache_version == local_cache_version):
                print(f"\n   ✅ CDN 数据是最新的（与本地一致）")
                print(f"   ✅ 测试通过：使用 @main 的 URL（通过 index.html 自动替换）可以获取到最新数据")
                return True
            else:
                print(f"\n   ⚠️  CDN 数据不是最新的")
                print(f"      - 本地: {local_last_updated} / {local_cache_version}")
                print(f"      - CDN:  {cdn_last_updated} / {cdn_cache_version}")
                return False
        else:
            print(f"   ❌ CDN 请求失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ CDN 请求失败: {e}")
        return False

if __name__ == "__main__":
    success = test_index_final()
    exit(0 if success else 1)

