"""
Windows Resource Allocation for Tkinter
Applies system-level optimizations for better UI performance
"""
import sys
import ctypes
import os


def is_admin():
    """Check if script is running with admin privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def set_process_priority_high():
    """
    Set the current Python process to HIGH priority
    This gives the UI more CPU time when competing with other processes
    """
    try:
        import win32process
        import win32api
        import win32con
        
        # Get current process handle
        pid = win32api.GetCurrentProcessId()
        handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
        
        # Set to HIGH_PRIORITY_CLASS (be careful - don't use REALTIME unless you know what you're doing)
        win32process.SetPriorityClass(handle, win32process.HIGH_PRIORITY_CLASS)
        
        print("✓ Process priority set to HIGH")
        return True
    except ImportError:
        print("⚠ win32process not available. Install with: pip install pywin32")
        return False
    except Exception as e:
        print(f"⚠ Could not set process priority: {e}")
        return False


def set_process_priority_above_normal():
    """
    Set process to ABOVE_NORMAL priority (safer than HIGH)
    Recommended for interactive applications
    """
    try:
        import win32process
        import win32api
        import win32con
        
        pid = win32api.GetCurrentProcessId()
        handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
        
        # ABOVE_NORMAL is safer for UI apps
        win32process.SetPriorityClass(handle, win32process.ABOVE_NORMAL_PRIORITY_CLASS)
        
        print("✓ Process priority set to ABOVE NORMAL")
        return True
    except ImportError:
        # Fallback using psutil
        try:
            import psutil
            p = psutil.Process(os.getpid())
            p.nice(psutil.HIGH_PRIORITY_CLASS)
            print("✓ Process priority elevated (using psutil)")
            return True
        except:
            print("⚠ Could not set process priority")
            return False
    except Exception as e:
        print(f"⚠ Could not set process priority: {e}")
        return False


def increase_working_set():
    """
    Increase the working set size for the process
    This reserves more RAM for the application
    """
    try:
        import win32api
        import win32process
        
        handle = win32api.GetCurrentProcess()
        
        # Set working set size (min 50MB, max 500MB)
        min_size = 50 * 1024 * 1024   # 50 MB
        max_size = 500 * 1024 * 1024  # 500 MB
        
        win32process.SetProcessWorkingSetSize(handle, min_size, max_size)
        
        print(f"✓ Working set size increased (50-500 MB reserved)")
        return True
    except ImportError:
        print("⚠ pywin32 not available for working set management")
        return False
    except Exception as e:
        print(f"⚠ Could not set working set size: {e}")
        return False


def enable_large_pages():
    """
    Enable large pages for better memory performance
    Requires admin privileges and specific Windows settings
    """
    if not is_admin():
        print("⚠ Large pages require administrator privileges")
        return False
    
    try:
        import ctypes
        from ctypes import wintypes
        
        # This is advanced and requires "Lock pages in memory" privilege
        # Not recommended unless you know what you're doing
        print("ℹ Large pages require 'Lock pages in memory' privilege")
        print("  To enable: secpol.msc > Local Policies > User Rights Assignment")
        return False
    except Exception as e:
        print(f"⚠ Large pages not available: {e}")
        return False


def disable_cpu_throttling():
    """
    Suggest disabling CPU throttling for better performance
    """
    print("\nℹ CPU Power Management Tips:")
    print("  1. Open Control Panel > Power Options")
    print("  2. Select 'High Performance' plan")
    print("  3. Click 'Change plan settings' > 'Change advanced power settings'")
    print("  4. Expand 'Processor power management'")
    print("  5. Set 'Minimum processor state' to 100%")
    print("  6. Set 'Maximum processor state' to 100%")
    print()


def optimize_windows_for_performance():
    """
    Provides instructions for Windows performance optimizations
    """
    print("\nℹ Windows System Optimizations:")
    print("  1. Disable Windows visual effects:")
    print("     • System > Advanced system settings")
    print("     • Performance Settings > 'Adjust for best performance'")
    print()
    print("  2. Disable startup programs:")
    print("     • Task Manager > Startup tab")
    print("     • Disable unnecessary programs")
    print()
    print("  3. Close background apps:")
    print("     • Settings > Privacy > Background apps")
    print("     • Turn off apps you don't need")
    print()
    print("  4. Update graphics drivers:")
    print("     • Check manufacturer website for latest drivers")
    print()


def set_process_affinity(cores=None):
    """
    Set CPU affinity to specific cores
    Useful for dedicating cores to your application
    """
    try:
        import psutil
        p = psutil.Process(os.getpid())
        
        if cores is None:
            # Use all cores
            cpu_count = psutil.cpu_count()
            cores = list(range(cpu_count))
        
        p.cpu_affinity(cores)
        print(f"✓ Process affinity set to cores: {cores}")
        return True
    except ImportError:
        print("⚠ psutil required for CPU affinity")
        return False
    except Exception as e:
        print(f"⚠ Could not set CPU affinity: {e}")
        return False


def get_system_info():
    """
    Display current system resource usage
    """
    print("\n" + "=" * 60)
    print("SYSTEM RESOURCE STATUS")
    print("=" * 60)
    
    try:
        import psutil
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        print(f"CPU Usage: {cpu_percent}% ({cpu_count} cores)")
        
        # Memory
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024**3)
        memory_total_gb = memory.total / (1024**3)
        print(f"Memory: {memory_used_gb:.1f}GB / {memory_total_gb:.1f}GB ({memory.percent}%)")
        
        # Current process
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info().rss / (1024**2)
        print(f"This Process: {process_memory:.1f}MB")
        
        # Recommendations
        print()
        if memory.percent > 80:
            print("⚠ WARNING: High memory usage. Consider closing other applications.")
        if cpu_percent > 80:
            print("⚠ WARNING: High CPU usage. Other processes may be competing for resources.")
        
        return True
    except ImportError:
        print("⚠ psutil not available. Install with: pip install psutil")
        return False


def apply_all_optimizations():
    """
    Apply all available optimizations
    """
    print("=" * 60)
    print("APPLYING WINDOWS RESOURCE OPTIMIZATIONS")
    print("=" * 60)
    print()
    
    results = []
    
    # 1. Process Priority (most important)
    print("1. Setting Process Priority...")
    if set_process_priority_above_normal():
        results.append("Priority")
    
    # 2. Working Set (memory allocation)
    print("\n2. Configuring Memory Allocation...")
    if increase_working_set():
        results.append("Memory")
    
    # 3. CPU Affinity (optional)
    print("\n3. CPU Affinity...")
    try:
        import psutil
        cpu_count = psutil.cpu_count()
        if cpu_count >= 4:
            # Use all but the first core (leave it for system)
            set_process_affinity(list(range(1, cpu_count)))
            results.append("CPU Affinity")
        else:
            print("  ℹ Skipping (less than 4 cores)")
    except:
        print("  ⚠ Could not configure CPU affinity")
    
    # 4. System Info
    print()
    get_system_info()
    
    # 5. Additional tips
    disable_cpu_throttling()
    optimize_windows_for_performance()
    
    # Summary
    print("=" * 60)
    print(f"OPTIMIZATION COMPLETE ({len(results)} applied)")
    print("=" * 60)
    print()
    if "Priority" in results:
        print("✓ Process priority elevated - Your app will get more CPU time")
    if "Memory" in results:
        print("✓ Memory reserved - Reduced memory allocation overhead")
    if "CPU Affinity" in results:
        print("✓ CPU cores assigned - Dedicated processing power")
    
    print()
    print("These optimizations will last until the application is closed.")
    print("For permanent improvements, follow the Windows optimization tips above.")
    print()
    
    return len(results) > 0


if __name__ == "__main__":
    print()
    
    # Check admin status
    if is_admin():
        print("✓ Running with administrator privileges")
    else:
        print("ℹ Running without administrator privileges (some features limited)")
    
    print()
    
    # Apply optimizations
    success = apply_all_optimizations()
    
    # Wait for user
    print("\nPress Enter to exit...")
    input()
    
    sys.exit(0 if success else 1)
