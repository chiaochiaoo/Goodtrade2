"""
UI Performance Optimization Utilities for Tkinter
Provides throttling, batching, and memory management tools
"""
import time
import psutil
import os
from functools import wraps
from collections import deque


class UIUpdateThrottler:
    """Throttle UI updates to prevent excessive redraws"""
    def __init__(self, min_interval_ms=50):
        self.min_interval_ms = min_interval_ms
        self.last_update = {}
        self.pending_updates = {}
        
    def throttle(self, key, func, *args, **kwargs):
        """Throttle function calls by key"""
        now = time.time() * 1000
        last = self.last_update.get(key, 0)
        
        if now - last >= self.min_interval_ms:
            self.last_update[key] = now
            func(*args, **kwargs)
        else:
            # Store for later execution
            self.pending_updates[key] = (func, args, kwargs)
    
    def flush_pending(self, root):
        """Execute all pending updates"""
        for key, (func, args, kwargs) in self.pending_updates.items():
            func(*args, **kwargs)
            self.last_update[key] = time.time() * 1000
        self.pending_updates.clear()


class BatchUpdateManager:
    """Batch multiple UI updates into a single operation"""
    def __init__(self, root, batch_delay_ms=100):
        self.root = root
        self.batch_delay_ms = batch_delay_ms
        self.pending_batches = {}
        self.after_ids = {}
        
    def add_to_batch(self, batch_key, update_func, *args, **kwargs):
        """Add an update to a batch"""
        if batch_key not in self.pending_batches:
            self.pending_batches[batch_key] = []
        
        self.pending_batches[batch_key].append((update_func, args, kwargs))
        
        # Cancel previous scheduled execution
        if batch_key in self.after_ids:
            self.root.after_cancel(self.after_ids[batch_key])
        
        # Schedule batch execution
        self.after_ids[batch_key] = self.root.after(
            self.batch_delay_ms, 
            lambda: self._execute_batch(batch_key)
        )
    
    def _execute_batch(self, batch_key):
        """Execute all updates in a batch"""
        if batch_key not in self.pending_batches:
            return
        
        updates = self.pending_batches.pop(batch_key)
        if batch_key in self.after_ids:
            del self.after_ids[batch_key]
        
        # Execute all updates
        for func, args, kwargs in updates:
            try:
                func(*args, **kwargs)
            except Exception as e:
                print(f"Batch update error: {e}")


class MemoryMonitor:
    """Monitor and optimize memory usage"""
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        
    def get_memory_usage_mb(self):
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / 1024 / 1024
    
    def get_memory_percent(self):
        """Get memory usage as percentage"""
        return self.process.memory_percent()
    
    def suggest_gc(self, threshold_mb=500):
        """Check if garbage collection is recommended"""
        return self.get_memory_usage_mb() > threshold_mb


class TreeviewOptimizer:
    """Optimize Treeview performance"""
    def __init__(self, treeview):
        self.treeview = treeview
        self._update_queue = deque(maxlen=1000)
        
    def batch_item_update(self, item_id, column, value):
        """Queue item updates for batch processing"""
        self._update_queue.append((item_id, column, value))
    
    def flush_updates(self):
        """Apply all queued updates at once"""
        # Temporarily disable view updates
        self.treeview.configure(takefocus=0)
        
        while self._update_queue:
            item_id, column, value = self._update_queue.popleft()
            try:
                if self.treeview.exists(item_id):
                    self.treeview.set(item_id, column, value)
            except Exception as e:
                print(f"Update error: {e}")
        
        self.treeview.configure(takefocus=1)
    
    def optimize_column_widths(self):
        """Set optimal column widths based on content"""
        for col in self.treeview["columns"]:
            max_width = len(str(col)) * 10  # Header width
            for item in self.treeview.get_children():
                val = str(self.treeview.set(item, col))
                max_width = max(max_width, len(val) * 8)
            self.treeview.column(col, width=min(max_width, 300))


def prioritize_process():
    """Set higher priority for the Python process"""
    try:
        import sys
        if sys.platform == 'win32':
            import win32process
            import win32api
            # Set to ABOVE_NORMAL priority
            handle = win32api.GetCurrentProcess()
            # Priority constants are in win32process, not win32con
            win32process.SetPriorityClass(handle, win32process.ABOVE_NORMAL_PRIORITY_CLASS)
            return True
    except ImportError:
        # Fallback for when win32 modules aren't available
        try:
            import psutil
            p = psutil.Process(os.getpid())
            if hasattr(psutil, 'HIGH_PRIORITY_CLASS'):
                p.nice(psutil.HIGH_PRIORITY_CLASS)
            return True
        except:
            pass
    except AttributeError:
        # If the constant doesn't exist, try psutil fallback
        try:
            import psutil
            p = psutil.Process(os.getpid())
            p.nice(psutil.HIGH_PRIORITY_CLASS)
            return True
        except:
            pass
    return False


def configure_tkinter_performance(root):
    """Apply performance configurations to Tkinter root window"""
    # Disable automatic geometry propagation for better control
    root.pack_propagate(False)
    
    # Configure for better rendering
    try:
        # Enable hardware acceleration on Windows
        root.attributes('-alpha', 0.99)  # Tiny bit of transparency enables GPU
        root.attributes('-alpha', 1.0)   # Then restore
    except:
        pass
    
    # Set better update priorities
    root.update_idletasks()
    
    return True
