#!/usr/bin/env python3
"""
测试前端逻辑：验证 @main 替换为 commit SHA 的逻辑
"""

import json
import requests
from pathlib import Path

def test_replace_main_with_sha():
    """测试替换逻辑"""
    print("=" * 60)
    print("测试前端逻辑：@main 替换为 commit SHA")
    print("=" * 60)
    
    # 读取本地文件获取 commit SHA
    local_file = Path("videos.json")
    with open(local_file, 'r', encoding='utf-8') as f:
        local_data = json.load(f)
    
    commit_sha = local_data.get('latestCommitSha')
    local_last_updated = local_data.get('lastUpdated')
    local_cache_version = local_data.get('cacheVersion')
    
    print(f"\n1. 本地数据:")
    print(f"   - Commit SHA: {commit_sha}")
    print(f"   - 更新时间: {local_last_updated}")
    print(f"   - 缓存版本: {local_cache_version}")
    
    if not commit_sha:
        print("\n❌ 未找到 commit SHA")
        return False
    
    # 测试替换逻辑
    print(f"\n2. 测试 URL 替换逻辑:")
    
    # 原始 URL（前端配置中的 @main）
    original_url = "https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/videos.json"
    print(f"   原始 URL: {original_url}")
    
    # 替换后的 URL（应该使用的）
    replaced_url = original_url.replace("@main", f"@{commit_sha}")
    print(f"   替换后 URL: {replaced_url}")
    
    # 测试使用 @main 的 URL（应该返回旧数据）
    print(f"\n3. 测试使用 @main 的 URL:")
    try:
        response = requests.get(original_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 请求成功")
            print(f"   - 更新时间: {data.get('lastUpdated')}")
            print(f"   - 缓存版本: {data.get('cacheVersion')}")
            
            if (data.get('lastUpdated') == local_last_updated and 
                data.get('cacheVersion') == local_cache_version):
                print(f"   ✅ @main 返回的是最新数据（意外）")
            else:
                print(f"   ❌ @main 返回的是旧数据（预期）")
                print(f"      - 本地: {local_last_updated} / {local_cache_version}")
                print(f"      - CDN:  {data.get('lastUpdated')} / {data.get('cacheVersion')}")
        else:
            print(f"   ❌ HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    # 测试使用 commit SHA 的 URL（应该返回最新数据）
    print(f"\n4. 测试使用 commit SHA 的 URL:")
    try:
        response = requests.get(replaced_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 请求成功")
            print(f"   - 更新时间: {data.get('lastUpdated')}")
            print(f"   - 缓存版本: {data.get('cacheVersion')}")
            
            if (data.get('lastUpdated') == local_last_updated and 
                data.get('cacheVersion') == local_cache_version):
                print(f"   ✅ 使用 commit SHA 返回的是最新数据（正确）")
                return True
            else:
                print(f"   ❌ 使用 commit SHA 返回的是旧数据（不应该）")
                print(f"      - 本地: {local_last_updated} / {local_cache_version}")
                print(f"      - CDN:  {data.get('lastUpdated')} / {data.get('cacheVersion')}")
        else:
            print(f"   ❌ HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    return False

if __name__ == "__main__":
    success = test_replace_main_with_sha()
    exit(0 if success else 1)

