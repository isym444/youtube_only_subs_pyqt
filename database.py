import sqlite3
import threading
import os
import time
from contextlib import contextmanager

class Database:
    _lock = threading.Lock()
    
    def __init__(self):
        # Get user's home directory
        user_data_dir = os.path.expanduser('~/Library/Application Support/YouTube Channel Tracker')
        
        # Create directory if it doesn't exist
        os.makedirs(user_data_dir, exist_ok=True)
        
        # Create database path
        self.db_path = os.path.join(user_data_dir, 'youtube_channels.db')
        
        # Initialize the database
        self._initialize_db()
    
    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            yield conn
        finally:
            if conn:
                conn.close()
    
    def _initialize_db(self):
        """Create the channels table if it doesn't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_name TEXT NOT NULL,
                    channel_id TEXT NOT NULL UNIQUE,
                    video_id TEXT,
                    video_title TEXT,
                    video_views TEXT,
                    upload_date TEXT,
                    has_new_video INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    def add_channel(self, channel_data):
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                with self._lock:
                    with self.get_connection() as conn:
                        cursor = conn.cursor()
                        
                        # Check if channel already exists
                        cursor.execute('SELECT channel_id FROM channels WHERE channel_id = ?', 
                                     (channel_data['channel_id'],))
                        
                        if cursor.fetchone() is None:
                            sql = '''INSERT INTO channels 
                                    (channel_name, channel_id, video_id, video_title, 
                                     video_views, upload_date, has_new_video) 
                                    VALUES (?, ?, ?, ?, ?, ?, ?)'''
                            
                            cursor.execute(sql, (
                                channel_data['channel_name'],
                                channel_data['channel_id'],
                                channel_data['video_id'],
                                channel_data['video_title'],
                                channel_data['video_views'],
                                channel_data['upload_date'],
                                channel_data.get('has_new_video', 1)
                            ))
                            conn.commit()
                            print(f"Successfully added channel: {channel_data['channel_name']}")
                            return True
                        else:
                            print(f"Channel already exists: {channel_data['channel_name']}")
                            return False
                            
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e):
                    retry_count += 1
                    print(f"Database locked, retrying... ({retry_count}/{max_retries})")
                    time.sleep(0.5)  # Reduced wait time
                else:
                    print(f"Database error: {e}")
                    return False
            except Exception as e:
                print(f"Error adding channel: {e}")
                return False
        
        print("Failed to add channel after maximum retries")
        return False
    
    def get_all_channels(self):
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM channels')
                return cursor.fetchall()
    
    def update_channel(self, channel_data):
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                sql = '''UPDATE channels 
                        SET video_id = ?, 
                            video_title = ?, 
                            video_views = ?, 
                            upload_date = ?,
                            has_new_video = ?
                        WHERE channel_id = ?'''
                
                cursor.execute(sql, (
                    channel_data['video_id'],
                    channel_data['video_title'],
                    channel_data['video_views'],
                    channel_data['upload_date'],
                    channel_data.get('has_new_video', 1),
                    channel_data['channel_id']
                ))
                conn.commit()
    
    def remove_channel(self, channel_id):
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM channels WHERE channel_id = ?', (channel_id,))
                conn.commit()
    
    def mark_video_as_watched(self, channel_id):
        try:
            self.cursor.execute("""
                UPDATE channels 
                SET has_new_video = 0 
                WHERE channel_id = ?
            """, (channel_id,))
            self.conn.commit()
        except Exception as e:
            print(f"Error marking video as watched: {str(e)}")
  