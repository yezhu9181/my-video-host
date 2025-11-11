#!/usr/bin/env python3
"""
测试 CDN 缓存 - 验证 CDN 返回的数据是否与本地文件一致
"""

import json
import requests
import time
from pathlib import Path

def test_cdn_cache():
    """测试 CDN 缓存"""
    local_file = Path("videos.json")
    cdn_url = "https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/videos.json"
    
    print("=" * 60)
    print("测试 CDN 缓存一致性")
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
    local_video_count = len(local_data.get('videos', []))
    
    print(f"   ✅ 本地文件读取成功")
    print(f"   - 更新时间: {local_last_updated}")
    print(f"   - 缓存版本: {local_cache_version}")
    print(f"   - 视频数量: {local_video_count}")
    
    # 从 CDN 获取数据（多次尝试，使用不同的缓存破坏参数）
    print(f"\n2. 从 CDN 获取数据...")
    print(f"   URL: {cdn_url}")
    
    max_attempts = 5
    cdn_data = None
    
    for attempt in range(1, max_attempts + 1):
        # 使用不同的缓存破坏参数
        cache_buster = f"?v={int(time.time())}&_t={time.time()}&attempt={attempt}&nocache=1"
        test_url = f"{cdn_url}{cache_buster}"
        
        print(f"\n   尝试 {attempt}/{max_attempts}: {test_url}")
        
        try:
            response = requests.get(test_url, 
                                  headers={
                                      'Cache-Control': 'no-cache, no-store, must-revalidate',
                                      'Pragma': 'no-cache',
                                      'Expires': '0'
                                  },
                                  timeout=10)
            
            if response.status_code == 200:
                cdn_data = response.json()
                cdn_last_updated = cdn_data.get('lastUpdated', 'N/A')
                cdn_cache_version = cdn_data.get('cacheVersion', 'N/A')
                cdn_video_count = len(cdn_data.get('videos', []))
                
                print(f"   ✅ CDN 请求成功")
                print(f"   - 更新时间: {cdn_last_updated}")
                print(f"   - 缓存版本: {cdn_cache_version}")
                print(f"   - 视频数量: {cdn_video_count}")
                
                # 比较关键字段
                if (cdn_last_updated == local_last_updated and 
                    cdn_cache_version == local_cache_version):
                    print(f"\n   ✅ 数据一致！CDN 返回的是最新数据")
                    break
                else:
                    print(f"\n   ⚠️  数据不一致，可能是缓存问题")
                    if attempt < max_attempts:
                        print(f"   等待 2 秒后重试...")
                        time.sleep(2)
            else:
                print(f"   ❌ HTTP {response.status_code}: {response.status_text}")
                
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
            if attempt < max_attempts:
                print(f"   等待 2 秒后重试...")
                time.sleep(2)
    
    # 详细比较
    print(f"\n3. 详细比较...")
    print("=" * 60)
    
    if cdn_data is None:
        print("❌ 无法从 CDN 获取数据")
        return False
    
    # 比较关键字段
    issues = []
    
    if cdn_data.get('lastUpdated') != local_data.get('lastUpdated'):
        issues.append(f"lastUpdated 不一致: 本地={local_data.get('lastUpdated')}, CDN={cdn_data.get('lastUpdated')}")
    
    if cdn_data.get('cacheVersion') != local_data.get('cacheVersion'):
        issues.append(f"cacheVersion 不一致: 本地={local_data.get('cacheVersion')}, CDN={cdn_data.get('cacheVersion')}")
    
    if len(cdn_data.get('videos', [])) != len(local_data.get('videos', [])):
        issues.append(f"视频数量不一致: 本地={len(local_data.get('videos', []))}, CDN={len(cdn_data.get('videos', []))}")
    
    # 比较每个视频的 lastUpdated
    local_videos = {v.get('filename'): v.get('lastUpdated') for v in local_data.get('videos', [])}
    cdn_videos = {v.get('filename'): v.get('lastUpdated') for v in cdn_data.get('videos', [])}
    
    for filename, local_updated in local_videos.items():
        cdn_updated = cdn_videos.get(filename)
        if cdn_updated != local_updated:
            issues.append(f"视频 {filename} 的 lastUpdated 不一致: 本地={local_updated}, CDN={cdn_updated}")
    
    if issues:
        print("❌ 发现不一致:")
        for issue in issues:
            print(f"   - {issue}")
        print("\n💡 建议:")
        print("   1. 等待几分钟后重试（CDN 缓存可能需要时间更新）")
        print("   2. 使用 GitHub API 获取最新数据（完全绕过 CDN 缓存）")
        print("   3. 检查 CDN 缓存清除是否成功")
        return False
    else:
        print("✅ 所有数据一致！CDN 返回的是最新数据")
        return True

if __name__ == "__main__":
    success = test_cdn_cache()
    exit(0 if success else 1)

