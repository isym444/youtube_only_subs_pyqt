import sqlite3
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('youtube_channels.db')
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_name TEXT,
                channel_id TEXT,
                video_id TEXT,
                video_title TEXT,
                video_views TEXT,
                upload_date TEXT,
                created_at TIMESTAMP,
                has_new_video BOOLEAN DEFAULT 0
            )
        ''')
        self.conn.commit()

    def add_channel(self, channel_data):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO channels (
                    channel_name, channel_id, video_id, video_title,
                    video_views, upload_date, created_at, has_new_video
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)
            ''', (
                str(channel_data['channel_name']),
                str(channel_data['channel_id']),
                str(channel_data['video_id']),
                str(channel_data['video_title']),
                str(channel_data['video_views']),
                str(channel_data['upload_date']),
                False
            ))
            self.conn.commit()
            print("Successfully added channel to database")
        except Exception as e:
            print(f"Database error: {e}")
            self.conn.rollback()

    def get_all_channels(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM channels ORDER BY created_at DESC')
        return cursor.fetchall()

    def update_channel_video(self, channel_id, video_data):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE channels 
            SET video_id = ?, video_title = ?, video_views = ?,
                upload_date = ?, has_new_video = ?
            WHERE channel_id = ?
        ''', (
            video_data['video_id'],
            video_data['video_title'],
            video_data['video_views'],
            video_data['upload_date'],
            True,
            channel_id
        ))
        self.conn.commit()

    def remove_channel(self, channel_id):
        query = "DELETE FROM channels WHERE channel_id = ?"
        self.cursor.execute(query, (channel_id,))
        self.conn.commit()
  