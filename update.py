#!/usr/bin/env python3
"""
视频库自动更新脚本 - 使用FFmpeg提取视频第一帧作为缩略图 + 缓存优化
"""

import os
import json
import glob
import subprocess
import base64
import time
import requests
from datetime import datetime
from pathlib import Path

class VideoLibraryUpdater:
    def __init__(self, repo_path=".", page_size=10, token_file_path="/Users/syh/git_token.txt"):
        self.repo_path = Path(repo_path)
        self.videos_path = self.repo_path / "videos"
        self.thumbnails_path = self.repo_path / "thumbnails"
        self.json_path = self.repo_path / "videos.json"
        self.page_size = page_size
        self.token_file_path = Path(token_file_path)
        
        # 缓存优化配置
        self.cache_version = self.get_cache_version()
        self.enable_cache_purge = True  # 是否启用CDN缓存清除
        
        # 检查FFmpeg是否可用
        self.ffmpeg_available = self.check_ffmpeg()
        
        # 初始化时读取token
        self.github_token = self.read_github_token()
        
        # 设置Git命令（使用读取的token）
        self.setup_git_commands()
        
        self.thumbnails_path.mkdir(exist_ok=True)
    
    def get_cache_version(self):
        """获取缓存版本号 - 使用Git commit SHA或时间戳"""
        try:
            # 使用Git commit SHA作为版本号（推荐）
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, cwd=self.repo_path
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        # 备用方案：使用时间戳
        return str(int(time.time()))
    
    def get_full_commit_sha(self):
        """获取完整的 Git commit SHA"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=self.repo_path
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None
    
    def generate_url_with_cache_buster(self, filename, file_type="video"):
        """生成带缓存破坏参数的URL"""
        base_url = f"https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main"
        
        if file_type == "video":
            url = f"{base_url}/videos/{filename}"
        else:
            url = f"{base_url}/thumbnails/{filename}"
        
        # 添加缓存破坏参数
        return f"{url}?v={self.cache_version}"
    
    def purge_cdn_cache(self, wait_after_push=True):
        """清除CDN缓存（缓存时间设置为0，确保获取最新数据）"""
        if not self.enable_cache_purge:
            print("ℹ️  CDN缓存清除已禁用")
            return False
            
        # 如果刚推送，等待一段时间确保 GitHub 已更新
        if wait_after_push:
            print("\n⏳ 等待 5 秒确保 GitHub 已更新...")
            time.sleep(5)
        
        print("\n🔄 清除CDN缓存（缓存时间=0）...")
        
        # 需要清除缓存的文件列表
        files_to_purge = [
            "/gh/yezhu9181/my-video-host@main/videos.json",
            # 可以根据需要添加其他关键文件
        ]
        
        success_count = 0
        
        # 清除 jsDelivr CDN 缓存（即使缓存时间设置为0，也主动清除以确保立即生效）
        for file_path in files_to_purge:
            try:
                purge_url = f"https://purge.jsdelivr.net{file_path}"
                print(f"   🔄 清除缓存: {file_path}")
                response = requests.get(purge_url, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('id'):
                        print(f"   ✅ jsDelivr 缓存清除请求已提交 (ID: {data.get('id')})")
                        success_count += 1
                    else:
                        print(f"   ⚠️  jsDelivr 缓存清除可能失败: {data}")
                else:
                    print(f"   ❌ jsDelivr 缓存清除失败: {file_path} - HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ jsDelivr 缓存清除错误: {e}")
        
        # 注意：其他 CDN（如 Statically、GitHack 等）可能没有公开的清除 API
        # 主要依赖前端添加缓存破坏参数来解决缓存问题
        print("💡 提示：其他 CDN 的缓存将依赖前端缓存破坏参数自动更新")
        print("💡 重要：即使清除了缓存，CDN 可能需要几分钟才能完全更新")
        print("💡 建议：前端应优先使用 GitHub API 获取最新数据（完全绕过 CDN 缓存）")
        
        return success_count > 0
    
    def verify_cdn_data(self, max_attempts=3, wait_seconds=3):
        """验证 CDN 数据是否已更新"""
        print("\n🔍 验证 CDN 数据是否已更新...")
        
        # 读取本地文件
        if not self.json_path.exists():
            print("   ⚠️  本地文件不存在，跳过验证")
            return False
        
        with open(self.json_path, 'r', encoding='utf-8') as f:
            local_data = json.load(f)
        
        local_last_updated = local_data.get('lastUpdated', '')
        local_cache_version = local_data.get('cacheVersion', '')
        
        cdn_url = "https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/videos.json"
        
        for attempt in range(1, max_attempts + 1):
            try:
                cache_buster = f"?v={int(time.time())}&_t={time.time()}&verify={attempt}"
                response = requests.get(f"{cdn_url}{cache_buster}", 
                                      headers={'Cache-Control': 'no-cache'},
                                      timeout=10)
                
                if response.status_code == 200:
                    cdn_data = response.json()
                    cdn_last_updated = cdn_data.get('lastUpdated', '')
                    cdn_cache_version = cdn_data.get('cacheVersion', '')
                    
                    if (cdn_last_updated == local_last_updated and 
                        cdn_cache_version == local_cache_version):
                        print(f"   ✅ CDN 数据已更新（尝试 {attempt}/{max_attempts}）")
                        print(f"      - 更新时间: {cdn_last_updated}")
                        print(f"      - 缓存版本: {cdn_cache_version}")
                        return True
                    else:
                        print(f"   ⚠️  CDN 数据尚未更新（尝试 {attempt}/{max_attempts}）")
                        print(f"      - 本地: {local_last_updated} / {local_cache_version}")
                        print(f"      - CDN:  {cdn_last_updated} / {cdn_cache_version}")
                        if attempt < max_attempts:
                            print(f"      - 等待 {wait_seconds} 秒后重试...")
                            time.sleep(wait_seconds)
                else:
                    print(f"   ❌ CDN 请求失败: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ 验证失败: {e}")
                if attempt < max_attempts:
                    time.sleep(wait_seconds)
        
        print(f"   ⚠️  CDN 数据可能尚未完全更新（已尝试 {max_attempts} 次）")
        print(f"   💡 建议：前端应使用 GitHub API 获取最新数据")
        return False
    
    def check_ffmpeg(self):
        """检查FFmpeg是否可用"""
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ FFmpeg可用")
                return True
            else:
                print("❌ FFmpeg不可用")
                return False
        except:
            print("❌ 未找到FFmpeg，将使用SVG占位图")
            return False
    
    def read_github_token(self):
        """从文件读取GitHub Token"""
        try:
            if self.token_file_path.exists():
                with open(self.token_file_path, 'r', encoding='utf-8') as f:
                    token = f.read().strip()
                    if token:
                        print(f"✅ 从 {self.token_file_path} 读取GitHub Token成功")
                        return token
                    else:
                        print(f"⚠️  Token文件为空: {self.token_file_path}")
            else:
                print(f"❌ Token文件不存在: {self.token_file_path}")
        except Exception as e:
            print(f"❌ 读取Token文件失败: {e}")
        
        return None
    
    def setup_git_commands(self):
        """设置Git命令"""
        if self.github_token:
            # 使用token的Git命令
            push_url = f"https://yezhu9181:{self.github_token}@github.com/yezhu9181/my-video-host.git"
            self.git_commands = [
                ["git", "add", "."],
                ["git", "commit", "-m", f"自动更新视频库 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
                ["git", "push", push_url, "main"]
            ]
            print("✅ Git命令已配置（使用Token认证）")
        else:
            # 不使用token的Git命令（可能会失败）
            self.git_commands = [
                ["git", "add", "."],
                ["git", "commit", "-m", f"自动更新视频库 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
                ["git", "push", "origin", "main"]
            ]
            print("⚠️  Git命令已配置（使用默认认证，可能需要手动输入凭据）")
    
    def get_video_files(self):
        """获取所有视频文件（返回完整路径）"""
        video_extensions = ['*.mp4', '*.MP4', '*.mov', '*.MOV', '*.avi', '*.AVI', '*.mkv', '*.MKV', '*.webm', '*.WEBM']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(glob.glob(str(self.videos_path / ext)))
        
        return [Path(f) for f in video_files]
    
    def encode_filename_to_base64(self, filename):
        """将文件名（不含扩展名）编码为base64"""
        name_without_ext = Path(filename).stem
        # 将文件名编码为base64
        encoded = base64.b64encode(name_without_ext.encode('utf-8')).decode('utf-8')
        # 将base64中的/替换为-，避免文件系统路径问题
        encoded = encoded.replace('/', '-')
        return encoded
    
    def is_base64_filename(self, filename):
        """检查文件名是否是base64格式"""
        name_without_ext = Path(filename).stem
        # base64字符串只包含A-Z, a-z, 0-9, +, -, =字符（/被替换为-）
        base64_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-=')
        if not all(c in base64_chars for c in name_without_ext):
            return False
        
        # 尝试解码
        try:
            # 将-替换回/用于解码
            test_str = name_without_ext.replace('-', '/')
            # 补齐等号
            padding = 4 - (len(test_str) % 4)
            if padding == 4:
                padding = 0
            test_str = test_str + '=' * padding
            decoded = base64.b64decode(test_str).decode('utf-8')
            # 如果解码成功且结果是可打印字符，认为是base64
            return decoded and all(ord(c) < 128 for c in decoded)
        except:
            return False
    
    def decode_base64_filename(self, filename):
        """从base64文件名解码出原始文件名"""
        name_without_ext = Path(filename).stem
        try:
            # 将-替换回/用于解码
            test_str = name_without_ext.replace('-', '/')
            # 补齐等号
            padding = 4 - (len(test_str) % 4)
            if padding == 4:
                padding = 0
            test_str = test_str + '=' * padding
            return base64.b64decode(test_str).decode('utf-8')
        except:
            return None
    
    def rename_video_to_base64(self, video_path):
        """将视频文件重命名为base64编码的名称"""
        original_path = Path(video_path)
        if not original_path.exists():
            return None
        
        # 获取原始文件名和扩展名
        original_name = original_path.name
        extension = original_path.suffix
        
        # 生成base64文件名
        base64_name = self.encode_filename_to_base64(original_name)
        new_filename = f"{base64_name}{extension}"
        new_path = original_path.parent / new_filename
        
        # 如果新文件名已存在且不是同一个文件，跳过重命名
        if new_path.exists() and new_path != original_path:
            print(f"  ⚠️  文件已存在，跳过重命名: {new_filename}")
            return new_filename
        
        # 重命名文件
        try:
            original_path.rename(new_path)
            print(f"  ✅ 重命名: {original_name} -> {new_filename}")
            return new_filename
        except Exception as e:
            print(f"  ❌ 重命名失败 {original_name}: {e}")
            return original_name
    
    def extract_video_thumbnail(self, video_filename):
        """使用FFmpeg提取视频第一帧作为缩略图"""
        video_path = self.videos_path / video_filename
        thumbnail_name = Path(video_filename).stem + ".jpg"
        thumbnail_path = self.thumbnails_path / thumbnail_name
        
        try:
            # 使用FFmpeg提取第一帧
            command = [
                "ffmpeg",
                "-i", str(video_path),
                "-ss", "00:00:01",  # 从第1秒开始（避免黑屏）
                "-vframes", "1",    # 只取1帧
                "-q:v", "2",        # 高质量（1-31，2是最高质量）
                "-y",               # 覆盖已存在文件
                str(thumbnail_path)
            ]
            
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and thumbnail_path.exists():
                print(f"  ✅ 生成缩略图: {thumbnail_name}")
                return thumbnail_name
            else:
                print(f"  ❌ FFmpeg提取失败: {result.stderr}")
                return self.create_svg_thumbnail(video_filename, self.get_file_size(video_filename))
                
        except subprocess.TimeoutExpired:
            print(f"  ⏰ FFmpeg提取超时")
            return self.create_svg_thumbnail(video_filename, self.get_file_size(video_filename))
        except Exception as e:
            print(f"  ❌ FFmpeg提取错误: {e}")
            return self.create_svg_thumbnail(video_filename, self.get_file_size(video_filename))
    
    def create_svg_thumbnail(self, video_filename, file_size_mb):
        """创建SVG缩略图（备用方案）"""
        thumbnail_name = Path(video_filename).stem + ".svg"
        thumbnail_path = self.thumbnails_path / thumbnail_name
        
        try:
            title = self.generate_friendly_title(Path(video_filename).stem)
            file_extension = Path(video_filename).suffix.upper()
            
            # 颜色方案
            if file_size_mb > 50:
                color_scheme = {"bg": "#4C1D95", "primary": "#8B5CF6", "secondary": "#C4B5FD"}
            elif file_size_mb > 20:
                color_scheme = {"bg": "#065F46", "primary": "#10B981", "secondary": "#6EE7B7"}
            else:
                color_scheme = {"bg": "#1E40AF", "primary": "#3B82F6", "secondary": "#93C5FD"}
            
            svg_content = f'''<svg width="320" height="180" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{color_scheme['bg']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1F2937;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bgGradient)" rx="8" ry="8"/>
  <g transform="translate(160, 70)">
    <circle r="28" fill="{color_scheme['primary']}" fill-opacity="0.9"/>
    <polygon points="-8,-10 -8,10 12,0" fill="#FFFFFF"/>
  </g>
  <g transform="translate(160, 120)">
    <text text-anchor="middle" fill="#F9FAFB" font-family="Arial, sans-serif" font-size="14" font-weight="bold">
      {title}
    </text>
    <text y="20" text-anchor="middle" fill="{color_scheme['secondary']}" font-family="Arial, sans-serif" font-size="11">
      {file_extension} • {file_size_mb} MB
    </text>
  </g>
</svg>'''
            
            with open(thumbnail_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            
            print(f"  ⚠️  使用SVG占位图: {thumbnail_name}")
            return thumbnail_name
            
        except Exception as e:
            print(f"  ❌ 创建SVG缩略图失败: {e}")
            return ""
    
    def get_video_info(self, video_filename):
        """使用FFmpeg获取视频详细信息"""
        video_path = self.videos_path / video_filename
        
        try:
            # 获取视频时长和分辨率
            command = [
                "ffmpeg",
                "-i", str(video_path)
            ]
            
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            
            duration = "0:00"
            resolution = "未知"
            
            # 解析输出获取时长
            for line in result.stderr.split('\n'):
                if "Duration" in line:
                    # 示例: Duration: 00:01:30.50
                    duration_str = line.split("Duration:")[1].split(",")[0].strip()
                    time_parts = duration_str.split(":")
                    if len(time_parts) >= 3:
                        hours = int(time_parts[0])
                        minutes = int(time_parts[1])
                        seconds = int(float(time_parts[2]))
                        if hours > 0:
                            duration = f"{hours}:{minutes:02d}:{seconds:02d}"
                        else:
                            duration = f"{minutes}:{seconds:02d}"
                
                # 解析分辨率
                if "Video:" in line and "x" in line:
                    # 示例: 1920x1080
                    import re
                    resolution_match = re.search(r'(\d+)x(\d+)', line)
                    if resolution_match:
                        width = resolution_match.group(1)
                        height = resolution_match.group(2)
                        resolution = f"{width}x{height}"
            
            return duration, resolution
            
        except:
            # 如果FFmpeg失败，使用估算方法
            return self.estimate_duration(video_filename), self.get_video_dimensions_from_filename(video_filename)
    
    def get_file_size(self, filename):
        """获取文件大小（MB）"""
        file_path = self.videos_path / filename
        if file_path.exists():
            size_bytes = file_path.stat().st_size
            return round(size_bytes / (1024 * 1024), 1)
        return 0
    
    def estimate_duration(self, filename):
        """估算视频时长（备用方法）"""
        size_mb = self.get_file_size(filename)
        estimated_seconds = int(size_mb / 0.25)  # 假设编码率为 2 Mbps
        estimated_seconds = min(estimated_seconds, 3600)
        
        if estimated_seconds < 60:
            return f"0:{estimated_seconds:02d}"
        else:
            minutes = estimated_seconds // 60
            seconds = estimated_seconds % 60
            return f"{minutes}:{seconds:02d}"
    
    def generate_video_data(self, video_files, existing_titles=None, original_to_base64_map=None):
        """生成视频数据（带缓存优化）"""
        if existing_titles is None:
            existing_titles = {}
        if original_to_base64_map is None:
            original_to_base64_map = {}
        
        videos = []
        
        for i, video_file in enumerate(sorted(video_files), 1):
            video_filename = video_file.name if isinstance(video_file, Path) else video_file
            print(f"📹 处理视频 {i}/{len(video_files)}: {video_filename}")
            
            name_without_ext = Path(video_filename).stem
            # 如果原有数据中有该视频文件的title，使用原有的值，否则生成新的
            # 先尝试用base64文件名查找，如果找不到，尝试用原始文件名查找
            title = None
            if video_filename in existing_titles and existing_titles[video_filename]:
                title = existing_titles[video_filename]
            else:
                # 尝试通过原始文件名查找（如果存在映射）
                for orig_name, base64_name in original_to_base64_map.items():
                    if base64_name == video_filename and orig_name in existing_titles:
                        title = existing_titles[orig_name]
                        break
            
            if not title:
                # 尝试从base64文件名解码出原始文件名来生成title
                decoded = self.decode_base64_filename(video_filename)
                if decoded:
                    title = self.generate_friendly_title(decoded)
                else:
                    # 如果解码失败，使用base64文件名本身
                    title = self.generate_friendly_title(name_without_ext)
            
            description = self.generate_description(title)
            file_size = self.get_file_size(video_filename)
            
            # 获取视频详细信息
            if self.ffmpeg_available:
                duration, resolution = self.get_video_info(video_filename)
            else:
                duration = self.estimate_duration(video_filename)
                resolution = self.get_video_dimensions_from_filename(video_filename)
            
            # 生成缩略图
            if self.ffmpeg_available:
                thumbnail_filename = self.extract_video_thumbnail(video_filename)
            else:
                thumbnail_filename = self.create_svg_thumbnail(video_filename, file_size)
            
            # 使用相对路径
            video_url = f"videos/{video_filename}"
            thumbnail_url = f"thumbnails/{thumbnail_filename}" if thumbnail_filename else ""
            
            video_data = {
                "id": i,
                "title": title,
                "filename": video_filename,
                "url": video_url,  # 相对路径：videos/文件名
                "description": description,
                "duration": duration,
                "size": f"{file_size} MB",
                "thumbnail": thumbnail_url,  # 相对路径：thumbnails/文件名
                "codec": "H.264",
                "resolution": resolution,
                "createdAt": datetime.now().strftime("%Y-%m-%d"),
                "thumbnailType": "JPG" if thumbnail_filename.endswith('.jpg') else "SVG",
                "cacheVersion": self.cache_version,  # 添加缓存版本信息
                "lastUpdated": datetime.now().isoformat()
            }
            
            videos.append(video_data)
        
        return videos
    
    def get_video_dimensions_from_filename(self, filename):
        """从文件名猜测视频分辨率"""
        name_lower = filename.lower()
        
        if any(x in name_lower for x in ['4k', '2160p', 'uhd']):
            return "3840x2160"
        elif any(x in name_lower for x in ['2k', '1440p']):
            return "2560x1440"
        elif any(x in name_lower for x in ['1080p', 'fullhd']):
            return "1920x1080"
        elif any(x in name_lower for x in ['720p', 'hd']):
            return "1280x720"
        else:
            size_mb = self.get_file_size(filename)
            if size_mb > 100:
                return "1920x1080"
            elif size_mb > 50:
                return "1280x720"
            else:
                return "854x480"
    
    def generate_friendly_title(self, filename):
        """生成友好的视频标题"""
        name = filename.replace('_', ' ').replace('-', ' ')
        
        name_mapping = {
            "intro": "产品介绍视频",
            "tutorial": "使用教程",
            "demo": "功能演示",
            "guide": "操作指南",
            "overview": "系统概览"
        }
        
        for key, value in name_mapping.items():
            if key in filename.lower():
                return value
        
        return name.title()
    
    def generate_description(self, title):
        """根据标题生成描述"""
        descriptions = {
            "产品介绍视频": "全面介绍产品的功能特性和使用场景",
            "使用教程": "详细的使用方法和操作步骤说明",
            "功能演示": "核心功能的实际使用演示",
            "操作指南": "具体的操作流程和注意事项",
            "系统概览": "系统整体架构和主要模块介绍"
        }
        
        return descriptions.get(title, f"这是关于{title}的详细说明视频")
    
    def run_git_commands(self):
        """执行Git命令"""
        print("\n🚀 开始执行Git命令...")
        print("=" * 50)
        
        success_count = 0
        total_commands = len(self.git_commands)
        
        for i, command in enumerate(self.git_commands, 1):
            # 隐藏token在日志中的显示
            log_command = command.copy()
            if 'push' in log_command and '@' in ' '.join(log_command):
                # 隐藏token部分
                push_cmd = ' '.join(log_command)
                safe_cmd = push_cmd.split('@')[0].split(':')[0] + '://***@' + push_cmd.split('@')[1]
                print(f"🔧 执行命令 {i}/{total_commands}: {safe_cmd}")
            else:
                print(f"🔧 执行命令 {i}/{total_commands}: {' '.join(command)}")
            
            try:
                # 切换到仓库目录
                original_cwd = os.getcwd()
                os.chdir(self.repo_path)
                
                # 执行Git命令
                result = subprocess.run(command, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    print(f"✅ 命令执行成功")
                    success_count += 1
                    
                    # 显示命令输出（如果有）
                    if result.stdout.strip():
                        print(f"   输出: {result.stdout.strip()}")
                else:
                    print(f"❌ 命令执行失败，返回码: {result.returncode}")
                    if result.stderr.strip():
                        # 过滤掉可能包含token的错误信息
                        error_msg = result.stderr.strip()
                        if '@' in error_msg and '://' in error_msg:
                            error_msg = error_msg.split('@')[0].split(':')[0] + '://***@' + error_msg.split('@')[1]
                        print(f"   错误: {error_msg}")
                
                # 切换回原目录
                os.chdir(original_cwd)
                
            except subprocess.TimeoutExpired:
                print(f"⏰ 命令执行超时")
            except Exception as e:
                print(f"❌ 执行命令时发生错误: {e}")
        
        print(f"\n📊 Git命令执行完成: {success_count}/{total_commands} 成功")
        return success_count == total_commands
    
    def check_git_status(self):
        """检查Git状态"""
        try:
            # 检查是否在Git仓库中
            result = subprocess.run(["git", "status"], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def update_videos_json(self):
        """更新videos.json文件"""
        print("🎬 视频库更新脚本 - 缓存优化版本")
        print("=" * 60)
        print(f"🆚 缓存版本: {self.cache_version}")
        
        # 显示FFmpeg状态
        if self.ffmpeg_available:
            print("✅ FFmpeg: 可用 - 将提取视频第一帧作为缩略图")
        else:
            print("⚠️  FFmpeg: 不可用 - 将使用SVG占位图")
        
        # 显示token状态
        if self.github_token:
            print("✅ GitHub Token: 已加载")
        else:
            print("⚠️  GitHub Token: 未找到，Git操作可能会失败")
        
        # 检查Git状态
        if not self.check_git_status():
            print("⚠️  警告: 当前目录不是Git仓库或Git未配置")
            print("💡 请确保:")
            print("   1. 已在Git仓库目录中")
            print("   2. Git已正确配置")
            print("   3. 有权限推送到远程仓库")
        
        if not self.videos_path.exists():
            print(f"❌ 错误: videos文件夹不存在")
            return False
        
        video_files = self.get_video_files()
        if not video_files:
            print("❌ 错误: 没有找到视频文件")
            return False
        
        print(f"📁 找到 {len(video_files)} 个视频文件")
        
        # 读取现有的videos.json文件，提取原有的title值
        existing_titles = {}
        if self.json_path.exists():
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if 'videos' in existing_data:
                        for video in existing_data['videos']:
                            filename = video.get('filename')
                            title = video.get('title')
                            if filename and title:
                                existing_titles[filename] = title
                if existing_titles:
                    print(f"📋 从现有文件读取到 {len(existing_titles)} 个视频的title")
            except Exception as e:
                print(f"⚠️  读取现有videos.json失败: {e}，将使用新生成的title")
        
        # 重命名视频文件为base64格式
        print("\n🔄 开始重命名视频文件为base64格式...")
        original_to_base64_map = {}
        renamed_files = []
        
        for video_path in video_files:
            original_name = video_path.name
            name_without_ext = video_path.stem
            
            # 检查文件名是否已经是base64格式
            is_base64 = self.is_base64_filename(original_name)
            
            if is_base64:
                print(f"  ✓ 文件已是base64格式: {original_name}")
                renamed_files.append(video_path)
            else:
                # 需要重命名
                new_filename = self.rename_video_to_base64(video_path)
                if new_filename and new_filename != original_name:
                    original_to_base64_map[original_name] = new_filename
                    # 更新路径为新文件名
                    renamed_files.append(self.videos_path / new_filename)
                else:
                    renamed_files.append(video_path)
        
        if original_to_base64_map:
            print(f"✅ 成功重命名 {len(original_to_base64_map)} 个文件")
        else:
            print("✅ 所有文件都已经是base64格式")
        
        videos = self.generate_video_data(renamed_files, existing_titles, original_to_base64_map)
        
        # 计算分页信息
        total_videos = len(videos)
        total_pages = (total_videos + self.page_size - 1) // self.page_size
        
        # 创建JSON数据
        updated_data = {
            "videos": videos,
            "pagination": {
                "total": total_videos,
                "page": 1,
                "pageSize": self.page_size,
                "totalPages": total_pages,
                "hasNext": False,
                "hasPrev": False
            },
            "lastUpdated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "repository": "https://github.com/yezhu9181/my-video-host",
            "ffmpegAvailable": self.ffmpeg_available,
            "cacheVersion": self.cache_version,  # 添加全局缓存版本
            "cachePolicy": {
                "maxAge": 0,  # CDN缓存时间设置为0（不缓存）
                "mustRevalidate": True,
                "noCache": True,
                "noStore": True
            },
            "apiEndpoints": {
                "allVideos": "/videos.json",
                "paginated": "/videos.json?page={page}&limit={limit}",
                "search": "/videos.json?search={keyword}",
                "byId": "/videos.json?id={id}"
            }
        }
        
        # 写入文件
        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n✅ 成功更新 videos.json")
            print(f"📊 统计信息:")
            print(f"   - 总视频数: {total_videos}")
            print(f"   - 每页数量: {self.page_size}")
            print(f"   - 总页数: {total_pages}")
            print(f"   - 缓存版本: {self.cache_version}")
            
            # 统计缩略图类型
            jpg_count = sum(1 for v in videos if v.get('thumbnailType') == 'JPG')
            svg_count = sum(1 for v in videos if v.get('thumbnailType') == 'SVG')
            print(f"   - JPG缩略图: {jpg_count}")
            print(f"   - SVG缩略图: {svg_count}")
            
            # 执行Git命令
            git_success = self.run_git_commands()
            
            # 获取最新的 commit SHA（在 Git 推送后）
            latest_commit_sha = None
            if git_success:
                latest_commit_sha = self.get_full_commit_sha()
                if latest_commit_sha:
                    print(f"📌 最新 commit SHA: {latest_commit_sha}")
                    # 更新 JSON 数据中的 commit SHA
                    updated_data["latestCommitSha"] = latest_commit_sha
                    # 重新写入文件以包含 commit SHA
                    with open(self.json_path, 'w', encoding='utf-8') as f:
                        json.dump(updated_data, f, ensure_ascii=False, indent=2)
                    print(f"✅ 已更新 videos.json，包含最新 commit SHA")
            
            if git_success:
                # 清除CDN缓存（等待 GitHub 更新）
                if self.enable_cache_purge:
                    purge_success = self.purge_cdn_cache(wait_after_push=True)
                    
                    # 验证 CDN 数据是否已更新（可选，可能需要等待）
                    if purge_success:
                        print("\n💡 提示：CDN 缓存清除请求已提交，但可能需要几分钟才能完全生效")
                        print("💡 建议：前端应使用 commit SHA 构建 CDN URL 以获取最新数据")
                
                print(f"\n🎉 所有任务完成！视频库已更新并推送到GitHub")
                print(f"🌐 访问地址: https://yezhu9181.github.io/my-video-host/")
                print(f"💡 缓存版本: {self.cache_version}")
                if latest_commit_sha:
                    print(f"💡 最新 commit SHA: {latest_commit_sha}")
                    print(f"💡 前端将使用 commit SHA 构建 CDN URL，确保获取最新数据")
            else:
                print(f"\n⚠️  视频数据已更新，但Git推送可能有问题")
                print(f"💡 请手动执行Git命令")
                print(f"💡 注意：如果文件未推送到 GitHub，CDN 无法获取最新数据")
            
            return True
            
        except Exception as e:
            print(f"❌ 写入文件失败: {e}")
            return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description='更新视频库配置并自动Git提交')
    parser.add_argument('--page-size', type=int, default=10, help='每页显示的视频数量')
    parser.add_argument('--no-git', action='store_true', help='不执行Git命令')
    parser.add_argument('--no-cache-purge', action='store_true', help='不清除CDN缓存')
    parser.add_argument('--token-file', default='/Users/syh/git_token.txt', help='GitHub Token文件路径')
    
    args = parser.parse_args()
    
    updater = VideoLibraryUpdater(page_size=args.page_size, token_file_path=args.token_file)
    
    # 如果指定了不执行Git命令，移除Git命令
    if args.no_git:
        updater.git_commands = []
        print("⚠️  Git命令已禁用")
    
    # 如果指定了不清除CDN缓存，禁用缓存清除
    if args.no_cache_purge:
        updater.enable_cache_purge = False
        print("⚠️  CDN缓存清除已禁用")
    
    success = updater.update_videos_json()
    
    if success:
        print("\n✅ 脚本执行完成")
    else:
        print("\n❌ 脚本执行失败")

if __name__ == "__main__":
    main()