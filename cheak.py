#!/usr/bin/env python3
"""
视频压缩脚本 - 检查并压缩大于19.5MB的视频文件
"""

import os
import glob
import subprocess
import shutil
from datetime import datetime
from pathlib import Path


class VideoCompressor:
    def __init__(self, videos_path="./videos", backup_path="/Users/syh/my-video-back", check_size_mb=19.5, target_size_mb=16):
        """
        初始化视频压缩器
        
        Args:
            videos_path: 视频文件夹路径
            backup_path: 备份文件夹路径
            check_size_mb: 检查阈值（大于此大小的文件会被压缩）
            target_size_mb: 压缩目标大小（压缩后文件大小）
        """
        self.videos_path = Path(videos_path)
        self.backup_path = Path(backup_path)
        self.check_size_mb = check_size_mb
        self.target_size_mb = target_size_mb
        
        # 检查FFmpeg是否可用
        self.ffmpeg_available = self.check_ffmpeg()
        
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
            print("❌ 未找到FFmpeg")
            return False
    
    def get_video_files(self):
        """获取所有视频文件"""
        video_extensions = ['*.mp4', '*.MP4', '*.mov', '*.MOV', '*.avi', '*.AVI', '*.mkv', '*.MKV', '*.webm', '*.WEBM']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(glob.glob(str(self.videos_path / ext)))
        
        return [Path(f).name for f in video_files]
    
    def get_file_size(self, filename):
        """获取文件大小（MB）"""
        file_path = self.videos_path / filename
        if file_path.exists():
            size_bytes = file_path.stat().st_size
            return round(size_bytes / (1024 * 1024), 1)
        return 0
    
    def compress_video_to_size(self, video_path, target_size_mb):
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
    
    def compress_large_videos(self):
        """检查并压缩所有大于指定大小的视频文件"""
        if not self.ffmpeg_available:
            print("⚠️  FFmpeg不可用，跳过视频压缩")
            return
        
        if not self.videos_path.exists():
            print(f"❌ 错误: videos文件夹不存在: {self.videos_path}")
            return
        
        print(f"\n📦 检查并压缩大于 {self.check_size_mb}MB 的视频文件（压缩到 {self.target_size_mb}MB）...")
        print("=" * 60)
        
        video_files = self.get_video_files()
        if not video_files:
            print("❌ 错误: 没有找到视频文件")
            return
        
        compressed_count = 0
        skipped_count = 0
        
        for video_file in video_files:
            video_path = self.videos_path / video_file
            file_size_mb = self.get_file_size(video_file)
            
            if file_size_mb > self.check_size_mb:
                print(f"\n🎬 发现大文件: {video_file} ({file_size_mb:.1f} MB)")
                if self.compress_video_to_size(video_path, self.target_size_mb):
                    compressed_count += 1
                else:
                    skipped_count += 1
            else:
                print(f"  ✓ {video_file} ({file_size_mb:.1f} MB) - 无需压缩")
        
        print(f"\n📊 压缩完成:")
        print(f"   - 已压缩: {compressed_count} 个文件")
        print(f"   - 跳过: {skipped_count} 个文件")
        print("=" * 60)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='检查并压缩大于19.5MB的视频文件')
    parser.add_argument('--videos-path', default='./videos', help='视频文件夹路径')
    parser.add_argument('--backup-path', default='/Users/syh/my-video-back', help='备份文件夹路径')
    parser.add_argument('--check-size', type=float, default=19.5, help='检查阈值（MB），大于此大小的文件会被压缩')
    parser.add_argument('--target-size', type=float, default=16, help='压缩目标大小（MB）')
    
    args = parser.parse_args()
    
    compressor = VideoCompressor(
        videos_path=args.videos_path,
        backup_path=args.backup_path,
        check_size_mb=args.check_size,
        target_size_mb=args.target_size
    )
    
    compressor.compress_large_videos()
    
    print("\n✅ 脚本执行完成")


if __name__ == "__main__":
    main()

