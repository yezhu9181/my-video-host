#!/usr/bin/env python3
"""
视频库自动更新脚本 - 使用FFmpeg提取视频第一帧作为缩略图
"""

import os
import json
import glob
import subprocess
from datetime import datetime
from pathlib import Path

class VideoLibraryUpdater:
    def __init__(self, repo_path=".", page_size=10, token_file_path="/Users/syh/git_token.txt", backup_path="/Users/syh/my-video-back"):
        self.repo_path = Path(repo_path)
        self.videos_path = self.repo_path / "videos"
        self.thumbnails_path = self.repo_path / "thumbnails"
        self.json_path = self.repo_path / "videos.json"
        self.page_size = page_size
        self.token_file_path = Path(token_file_path)
        self.backup_path = Path(backup_path)
        
        # 检查FFmpeg是否可用
        self.ffmpeg_available = self.check_ffmpeg()
        
        # 初始化时读取token
        self.github_token = self.read_github_token()
        
        # 设置Git命令（使用读取的token）
        self.setup_git_commands()
        
        self.thumbnails_path.mkdir(exist_ok=True)
        # 确保备份目录存在
        self.backup_path.mkdir(parents=True, exist_ok=True)
    
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
        """获取所有视频文件"""
        video_extensions = ['*.mp4', '*.MP4', '*.mov', '*.MOV', '*.avi', '*.AVI', '*.mkv', '*.MKV', '*.webm', '*.WEBM']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(glob.glob(str(self.videos_path / ext)))
        
        return [Path(f).name for f in video_files]
    
    def compress_video_to_size(self, video_path, target_size_mb=19.9):
        """使用FFmpeg压缩视频到指定大小（MB），严格小于等于目标大小"""
        video_path = Path(video_path)
        if not video_path.exists():
            return False
        
        # 获取视频时长（秒）- 使用ffmpeg获取
        try:
            duration_command = [
                "ffmpeg",
                "-i", str(video_path)
            ]
            result = subprocess.run(duration_command, capture_output=True, text=True, timeout=10)
            
            duration = 0
            # 从stderr中解析时长（ffmpeg将信息输出到stderr）
            for line in result.stderr.split('\n'):
                if "Duration" in line:
                    # 示例: Duration: 00:01:30.50
                    try:
                        duration_str = line.split("Duration:")[1].split(",")[0].strip()
                        time_parts = duration_str.split(":")
                        if len(time_parts) >= 3:
                            hours = float(time_parts[0])
                            minutes = float(time_parts[1])
                            seconds = float(time_parts[2])
                            duration = hours * 3600 + minutes * 60 + seconds
                            break
                    except:
                        continue
            
            if duration <= 0:
                print(f"  ⚠️  无法解析视频时长，跳过压缩")
                return False
        except Exception as e:
            print(f"  ⚠️  无法获取视频时长: {e}，跳过压缩")
            return False
        
        # 计算初始目标比特率（kbps）
        # 目标大小（MB）* 8（转换为Mbit）* 1024（转换为kbit）/ 时长（秒）
        # 预留一些空间给音频（假设音频128kbps）
        audio_bitrate = 128
        target_bitrate_kbps = int((target_size_mb * 8 * 1024) / duration - audio_bitrate)
        
        # 确保比特率不会太低（至少500kbps）
        target_bitrate_kbps = max(target_bitrate_kbps, 500)
        
        # 创建临时输出文件
        temp_output = video_path.parent / f"{video_path.stem}_compressed{video_path.suffix}"
        
        # 循环压缩，直到文件大小严格小于等于目标大小
        max_attempts = 5
        attempt = 0
        import shutil
        last_compressed_size = None
        current_bitrate = target_bitrate_kbps
        
        while attempt < max_attempts:
            attempt += 1
            
            # 如果之前尝试过，根据实际文件大小调整比特率
            if attempt > 1 and last_compressed_size:
                # 根据实际大小和目标大小的比例来调整比特率
                # 如果实际大小是目标的1.2倍，则比特率应该降低到原来的 1/1.2
                ratio = last_compressed_size / target_size_mb
                current_bitrate = int(current_bitrate / ratio * 0.95)  # 再降低5%以确保安全
                print(f"  🔄 第 {attempt} 次尝试，根据上次结果调整比特率至 {current_bitrate}kbps...")
            elif attempt > 1:
                # 如果没有上次的大小信息，降低10%的比特率
                current_bitrate = int(current_bitrate * 0.9)
                print(f"  🔄 第 {attempt} 次尝试，降低比特率至 {current_bitrate}kbps...")
            
            try:
                # 清理之前的日志文件
                log_files = [
                    video_path.parent / "ffmpeg2pass-0.log",
                    video_path.parent / "ffmpeg2pass-0.log.mbtree"
                ]
                for log_file in log_files:
                    if log_file.exists():
                        try:
                            log_file.unlink()
                        except:
                            pass
                
                # 使用两遍编码来精确控制文件大小
                # 第一遍：分析视频
                pass1_command = [
                    "ffmpeg",
                    "-i", str(video_path),
                    "-c:v", "libx264",
                    "-b:v", f"{current_bitrate}k",
                    "-pass", "1",
                    "-passlogfile", str(video_path.parent / "ffmpeg2pass"),
                    "-an",  # 第一遍不编码音频
                    "-f", "null",
                    "-y",
                    "/dev/null" if os.name != 'nt' else "NUL"
                ]
                
                if attempt == 1:
                    print(f"  🔄 开始压缩（第一遍分析）...")
                result1 = subprocess.run(pass1_command, capture_output=True, text=True, timeout=300)
                
                if result1.returncode != 0:
                    print(f"  ❌ 第一遍编码失败: {result1.stderr[:200]}")
                    if temp_output.exists():
                        temp_output.unlink()
                    return False
                
                # 第二遍：实际编码
                pass2_command = [
                    "ffmpeg",
                    "-i", str(video_path),
                    "-c:v", "libx264",
                    "-b:v", f"{current_bitrate}k",
                    "-pass", "2",
                    "-passlogfile", str(video_path.parent / "ffmpeg2pass"),
                    "-c:a", "aac",
                    "-b:a", f"{audio_bitrate}k",
                    "-movflags", "+faststart",  # 优化网络播放
                    "-y",
                    str(temp_output)
                ]
                
                if attempt == 1:
                    print(f"  🔄 开始压缩（第二遍编码）...")
                result2 = subprocess.run(pass2_command, capture_output=True, text=True, timeout=600)
                
                # 清理两遍编码的日志文件
                for log_file in log_files:
                    if log_file.exists():
                        try:
                            log_file.unlink()
                        except:
                            pass
                
                if result2.returncode == 0 and temp_output.exists():
                    # 检查压缩后的文件大小（严格小于等于目标大小）
                    compressed_size_mb = temp_output.stat().st_size / (1024 * 1024)
                    
                    if compressed_size_mb <= target_size_mb:
                        # 将原文件移动到备份目录
                        backup_path = self.backup_path / video_path.name
                        try:
                            # 如果备份目录中已存在同名文件，添加时间戳
                            if backup_path.exists():
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                backup_path = self.backup_path / f"{video_path.stem}_{timestamp}{video_path.suffix}"
                            
                            # 移动原文件到备份目录
                            shutil.move(str(video_path), str(backup_path))
                            # 将压缩后的文件移动到原位置
                            shutil.move(str(temp_output), str(video_path))
                            print(f"  ✅ 压缩成功: {compressed_size_mb:.2f} MB (原文件已移动到 {self.backup_path})")
                            return True
                        except Exception as e:
                            print(f"  ❌ 移动文件失败: {e}")
                            if temp_output.exists():
                                temp_output.unlink()
                            return False
                    else:
                        print(f"  ⚠️  压缩后文件大小 {compressed_size_mb:.2f} MB 仍大于目标 {target_size_mb} MB，继续尝试...")
                        last_compressed_size = compressed_size_mb  # 记录本次压缩后的大小
                        if temp_output.exists():
                            temp_output.unlink()
                        # 继续循环，降低比特率重试
                        continue
                else:
                    print(f"  ❌ 第二遍编码失败: {result2.stderr[:200] if result2.stderr else '未知错误'}")
                    if temp_output.exists():
                        temp_output.unlink()
                    return False
                    
            except subprocess.TimeoutExpired:
                print(f"  ⏰ 压缩超时")
                if temp_output.exists():
                    temp_output.unlink()
                return False
            except Exception as e:
                print(f"  ❌ 压缩过程出错: {e}")
                if temp_output.exists():
                    temp_output.unlink()
                return False
        
        # 如果所有尝试都失败
        print(f"  ❌ 经过 {max_attempts} 次尝试，仍无法压缩到目标大小")
        if temp_output.exists():
            temp_output.unlink()
        return False
    
    def compress_large_videos(self, max_size_mb=20):
        """检查并压缩所有大于指定大小的视频文件（默认检查大于20MB的文件，压缩到19.9MB）"""
        if not self.ffmpeg_available:
            print("⚠️  FFmpeg不可用，跳过视频压缩")
            return
        
        print(f"\n📦 检查并压缩大于 {max_size_mb}MB 的视频文件...")
        print("=" * 60)
        
        video_files = self.get_video_files()
        compressed_count = 0
        skipped_count = 0
        
        for video_file in video_files:
            video_path = self.videos_path / video_file
            file_size_mb = self.get_file_size(video_file)
            
            if file_size_mb > max_size_mb:
                print(f"\n🎬 发现大文件: {video_file} ({file_size_mb:.1f} MB)")
                # 压缩到19.9MB（严格小于等于19.9MB）
                if self.compress_video_to_size(video_path, target_size_mb=19.9):
                    compressed_count += 1
                else:
                    skipped_count += 1
            else:
                print(f"  ✓ {video_file} ({file_size_mb:.1f} MB) - 无需压缩")
        
        print(f"\n📊 压缩完成:")
        print(f"   - 已压缩: {compressed_count} 个文件")
        print(f"   - 跳过: {skipped_count} 个文件")
        print("=" * 60)
    
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
    
    def generate_video_data(self, video_files):
        """生成视频数据"""
        videos = []
        
        for i, video_file in enumerate(sorted(video_files), 1):
            print(f"📹 处理视频 {i}/{len(video_files)}: {video_file}")
            
            name_without_ext = Path(video_file).stem
            title = self.generate_friendly_title(name_without_ext)
            description = self.generate_description(title)
            file_size = self.get_file_size(video_file)
            
            # 获取视频详细信息
            if self.ffmpeg_available:
                duration, resolution = self.get_video_info(video_file)
            else:
                duration = self.estimate_duration(video_file)
                resolution = self.get_video_dimensions_from_filename(video_file)
            
            # 生成缩略图
            if self.ffmpeg_available:
                thumbnail_filename = self.extract_video_thumbnail(video_file)
            else:
                thumbnail_filename = self.create_svg_thumbnail(video_file, file_size)
            
            thumbnail_url = f"https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/thumbnails/{thumbnail_filename}" if thumbnail_filename else ""
            
            video_data = {
                "id": i,
                "title": title,
                "filename": video_file,
                "url": f"https://cdn.jsdelivr.net/gh/yezhu9181/my-video-host@main/videos/{video_file}",
                "description": description,
                "duration": duration,
                "size": f"{file_size} MB",
                "thumbnail": thumbnail_url,
                "codec": "H.264",
                "resolution": resolution,
                "createdAt": datetime.now().strftime("%Y-%m-%d"),
                "thumbnailType": "JPG" if thumbnail_filename.endswith('.jpg') else "SVG"
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
        print("🎬 视频库更新脚本 - 使用FFmpeg提取缩略图")
        print("=" * 60)
        
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
        
        # 在更新文件之前，压缩大于20MB的视频文件（压缩到19.9MB）
        self.compress_large_videos(max_size_mb=20)
        
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
            "repository": "https://github.com/yezhu9181/my-video-host",
            "ffmpegAvailable": self.ffmpeg_available,
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
            
            # 统计缩略图类型
            jpg_count = sum(1 for v in videos if v.get('thumbnailType') == 'JPG')
            svg_count = sum(1 for v in videos if v.get('thumbnailType') == 'SVG')
            print(f"   - JPG缩略图: {jpg_count}")
            print(f"   - SVG缩略图: {svg_count}")
            
            # 执行Git命令
            git_success = self.run_git_commands()
            
            if git_success:
                print(f"\n🎉 所有任务完成！视频库已更新并推送到GitHub")
                print(f"🌐 访问地址: https://yezhu9181.github.io/my-video-host/")
            else:
                print(f"\n⚠️  视频数据已更新，但Git推送可能有问题")
                print(f"💡 请手动执行Git命令")
            
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
    
    # 如果指定了不执行Git命令，移除Git命令
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
