#!/usr/bin/env python3
"""
视频库更新脚本 - 修复版本
"""

import os
import json
import glob
import subprocess
import base64
import time
from datetime import datetime
from pathlib import Path

class VideoLibraryUpdater:
    def __init__(self, repo_path=".", page_size=10, token_file_path="/Users/syh/git_token.txt"):
        self.repo_path = Path(repo_path)
        self.videos_path = self.repo_path / "videos"
        self.thumbnails_path = self.repo_path / "thumbnails"
        self.page_size = page_size
        self.token_file_path = Path(token_file_path)
        
        # 生成唯一的JSON文件名（使用时间戳）
        self.timestamp = int(time.time())
        self.json_filename = f"videos_{self.timestamp}.json"
        self.json_path = self.repo_path / self.json_filename
        
        # 检查FFmpeg是否可用
        self.ffmpeg_available = self.check_ffmpeg()
        
        # 初始化时读取token
        self.github_token = self.read_github_token()
        
        self.thumbnails_path.mkdir(exist_ok=True)
    
    def generate_unique_url(self, filename, file_type="video"):
        """生成唯一URL - 使用时间戳文件名"""
        base_url = f"https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main"
        
        if file_type == "video":
            return f"{base_url}/videos/{filename}"
        else:
            return f"{base_url}/thumbnails/{filename}"
    
    def update_main_json(self):
        """更新主videos.json文件，指向最新的数据文件"""
        main_json_path = self.repo_path / "videos.json"
        
        main_data = {
            "latest": self.json_filename,
            "timestamp": self.timestamp,
            "lastUpdated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "dataUrl": f"https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/{self.json_filename}",
            "message": "使用 latest 字段指向当前有效的数据文件"
        }
        
        with open(main_json_path, 'w', encoding='utf-8') as f:
            json.dump(main_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 更新主索引文件: videos.json -> {self.json_filename}")

    def get_video_files(self):
        """获取所有视频文件（返回完整路径）"""
        video_extensions = ['*.mp4', '*.MP4', '*.mov', '*.MOV', '*.avi', '*.AVI', '*.mkv', '*.MKV', '*.webm', '*.WEBM']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(glob.glob(str(self.videos_path / ext)))
        
        return [Path(f) for f in video_files]
    
    def setup_git_commands(self):
        """设置Git命令"""
        if self.github_token:
            push_url = f"https://yezhu9181:{self.github_token}@github.com/yezhu9181/my-video-host.git"
            self.git_commands = [
                ["git", "add", "."],
                ["git", "commit", "-m", f"视频库更新 {self.timestamp} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
                ["git", "push", push_url, "main"]
            ]
            print("✅ Git命令已配置")
        else:
            self.git_commands = [
                ["git", "add", "."],
                ["git", "commit", "-m", f"视频库更新 {self.timestamp}"],
                ["git", "push", "origin", "main"]
            ]
            print("⚠️  Git命令已配置（使用默认认证）")
    
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

    def generate_video_data(self, video_files):
        """生成视频数据"""
        videos = []
        
        for i, video_file in enumerate(sorted(video_files), 1):
            video_filename = video_file.name
            print(f"📹 处理视频 {i}/{len(video_files)}: {video_filename}")
            
            name_without_ext = Path(video_filename).stem
            title = self.generate_friendly_title(name_without_ext)
            description = self.generate_description(title)
            file_size = self.get_file_size(video_filename)
            
            # 获取视频信息
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
            
            video_url = self.generate_unique_url(video_filename, "video")
            thumbnail_url = self.generate_unique_url(thumbnail_filename, "thumbnail") if thumbnail_filename else ""
            
            video_data = {
                "id": i,
                "title": title,
                "filename": video_filename,
                "url": video_url,
                "description": description,
                "duration": duration,
                "size": f"{file_size} MB",
                "thumbnail": thumbnail_url,
                "codec": "H.264",
                "resolution": resolution,
                "createdAt": datetime.now().strftime("%Y-%m-%d"),
                "thumbnailType": "JPG" if thumbnail_filename.endswith('.jpg') else "SVG",
                "timestamp": self.timestamp
            }
            
            videos.append(video_data)
        
        return videos

    def update_videos_json(self):
        """更新视频数据文件"""
        print("🎬 视频库更新脚本 - 修复版本")
        print("=" * 60)
        print(f"🆚 数据文件: {self.json_filename}")
        
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
        
        if not self.videos_path.exists():
            print(f"❌ 错误: videos文件夹不存在")
            return False
        
        video_files = self.get_video_files()
        if not video_files:
            print("❌ 错误: 没有找到视频文件")
            return False
        
        print(f"📁 找到 {len(video_files)} 个视频文件")
        
        videos = self.generate_video_data(video_files)
        
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
            "timestamp": self.timestamp,
            "filename": self.json_filename,
            "repository": "https://github.com/yezhu9181/my-video-host",
            "ffmpegAvailable": self.ffmpeg_available
        }
        
        # 写入文件
        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, ensure_ascii=False, indent=2)
            
            # 更新主索引文件
            self.update_main_json()
            
            print(f"\n✅ 成功生成数据文件: {self.json_filename}")
            print(f"📊 统计信息:")
            print(f"   - 总视频数: {total_videos}")
            print(f"   - 每页数量: {self.page_size}")
            print(f"   - 总页数: {total_pages}")
            print(f"   - 时间戳: {self.timestamp}")
            
            # 统计缩略图类型
            jpg_count = sum(1 for v in videos if v.get('thumbnailType') == 'JPG')
            svg_count = sum(1 for v in videos if v.get('thumbnailType') == 'SVG')
            print(f"   - JPG缩略图: {jpg_count}")
            print(f"   - SVG缩略图: {svg_count}")
            
            # 执行Git命令
            git_success = self.run_git_commands()
            
            if git_success:
                print(f"\n🎉 所有任务完成！")
                print(f"🌐 最新数据文件: {self.json_filename}")
                print(f"💡 CDN将立即加载新文件，无缓存问题")
            else:
                print(f"\n⚠️  数据文件已生成，但Git推送可能有问题")
            
            return True
            
        except Exception as e:
            print(f"❌ 写入文件失败: {e}")
            return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description='更新视频库配置并自动Git提交')
    parser.add_argument('--page-size', type=int, default=10, help='每页显示的视频数量')
    parser.add_argument('--no-git', action='store_true', help='不执行Git命令')
    parser.add_argument('--token-file', default='/Users/syh/git_token.txt', help='GitHub Token文件路径')
    
    args = parser.parse_args()
    
    updater = VideoLibraryUpdater(page_size=args.page_size, token_file_path=args.token_file)
    
    if args.no_git:
        updater.git_commands = []
        print("⚠️  Git命令已禁用")
    
    success = updater.update_videos_json()
    
    if success:
        print("\n✅ 脚本执行完成")
    else:
        print("\n❌ 脚本执行失败")

if __name__ == "__main__":
    main()