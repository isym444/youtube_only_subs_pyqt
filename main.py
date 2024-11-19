import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLineEdit, QPushButton, QGridLayout, 
                            QLabel, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkProxy, QSslConfiguration, QSsl
from PyQt6.QtGui import QPixmap
import asyncio
# import aiotube  # Remove or comment out this line
from aiotube import Channel, Search, Video  # Add this line instead
from database import Database
import qasync
import webbrowser
import requests

class ChannelInfoWindow(QWidget):
    def __init__(self, search_results, parent=None):
        super().__init__()
        self.search_results = search_results  # Now expects a list of channels
        self.parent = parent
        self.setWindowTitle("Channel Information")
        self.setGeometry(200, 200, 400, 600)  # Made taller to accommodate multiple channels
        
        layout = QVBoxLayout()
        
        # Create a scroll area for multiple channels
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Add each channel's information
        for channel_data in search_results:
            channel_widget = QWidget()
            channel_layout = QVBoxLayout()
            
            # Create horizontal layout for avatar and basic info
            header_layout = QHBoxLayout()
            
            # Create and setup avatar label
            avatar_label = QLabel()
            avatar_label.setFixedSize(50, 50)
            if 'avatar' in channel_data and channel_data['avatar']:
                try:
                    # Add https: scheme if URL starts with //
                    avatar_url = channel_data['avatar']
                    if avatar_url.startswith('//'):
                        avatar_url = 'https:' + avatar_url
                    
                    # Download and set avatar image
                    response = requests.get(avatar_url)
                    pixmap = QPixmap()
                    if pixmap.loadFromData(response.content):
                        scaled_pixmap = pixmap.scaled(
                            50, 50,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        avatar_label.setPixmap(scaled_pixmap)
                except Exception as e:
                    print(f"Error loading avatar: {e}")
            
            # Create vertical layout for name and subscribers
            info_layout = QVBoxLayout()
            channel_name = QLabel(f"Channel: {channel_data['name']}")
            subscribers = QLabel(f"Subscribers: {channel_data['subscribers']}")
            
            info_layout.addWidget(channel_name)
            info_layout.addWidget(subscribers)
            
            # Add avatar and info to header layout
            header_layout.addWidget(avatar_label)
            header_layout.addLayout(info_layout)
            header_layout.addStretch()
            
            # Add header layout to main channel layout
            channel_layout.addLayout(header_layout)
            
            # Display channel info
            description = QLabel(f"Description: {channel_data['description'][:200]}...")
            description.setWordWrap(True)
            channel_id = QLabel(f"ID: {channel_data['channel_id']}")
            
            # Style the labels
            for label in [channel_name, subscribers, description, channel_id]:
                label.setStyleSheet("color: white;")
            
            channel_layout.addWidget(channel_name)
            channel_layout.addWidget(subscribers)
            channel_layout.addWidget(description)
            channel_layout.addWidget(channel_id)
            
            # Add Channel button for this specific channel
            add_button = QPushButton("Add Channel")
            add_button.clicked.connect(lambda checked, cd=channel_data: 
                asyncio.create_task(self.add_channel(cd)))
            add_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    padding: 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            channel_layout.addWidget(add_button)
            
            # Add a separator line except for the last channel
            if channel_data != search_results[-1]:
                separator = QFrame()
                separator.setFrameShape(QFrame.Shape.HLine)
                separator.setStyleSheet("background-color: #555;")
                channel_layout.addWidget(separator)
            
            channel_widget.setLayout(channel_layout)
            scroll_layout.addWidget(channel_widget)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
        
        # Style the window
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
            }
        """)

    async def add_channel(self, channel_data):
        try:
            # Get channel data
            channel = Channel(channel_data['channel_id'])
            metadata = channel.metadata
            
            # Get latest video
            latest_video_id = channel.last_uploaded
            if not latest_video_id:
                print("Could not fetch latest video ID")
                return

            print(f"Latest video ID: {latest_video_id}")
            
            try:
                # Get video details
                video = Video(latest_video_id)
                video_metadata = video.metadata
                
                # Prepare channel data for database
                channel_data = {
                    'channel_name': metadata.get('name', 'Unknown Channel'),
                    'channel_id': channel_data['channel_id'],
                    'video_id': latest_video_id,
                    'video_title': video_metadata.get('title', 'Video information unavailable'),
                    'video_views': str(video_metadata.get('views', 'N/A')),
                    'upload_date': str(video_metadata.get('upload_date', 'N/A'))
                }
                
                print(f"Saving channel data: {channel_data}")
                
                # Save to database and update UI
                self.parent.db.add_channel(channel_data)
                await self.parent.load_channels()
                
            except Exception as video_error:
                print(f"Error fetching video data: {video_error}")
        
        except Exception as e:
            print(f"Error in add_channel: {str(e)}")

class VideoCard(QWidget):
    clicked = pyqtSignal()
    removed = pyqtSignal(str)  # New signal for removal
    
    def __init__(self, video_data, parent=None):
        super().__init__()
        self.video_data = video_data
        self.parent = parent  # Store parent reference
        
        layout = QVBoxLayout()
        
        # Create thumbnail label
        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(320, 180)  # 16:9 aspect ratio
        self.thumbnail.setStyleSheet("""
            QLabel {
                background-color: #1f1f1f;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.thumbnail)
        
        # Load thumbnail
        self.load_thumbnail(video_data['video_id'])
        
        # Create labels for video information
        channel_name = QLabel(video_data['channel_name'])
        video_title = QLabel(video_data['video_title'])
        video_views = QLabel(f"Views: {video_data['video_views']}")
        upload_date = QLabel(f"Uploaded: {video_data['upload_date']}")
        
        # Style labels
        channel_name.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        video_title.setStyleSheet("color: white; font-size: 12px;")
        video_views.setStyleSheet("color: white; font-size: 11px;")
        upload_date.setStyleSheet("color: white; font-size: 11px;")
        
        for label in [channel_name, video_title, video_views, upload_date]:
            label.setWordWrap(True)
        
        # Add widgets to layout
        layout.addWidget(channel_name)
        layout.addWidget(video_title)
        layout.addWidget(video_views)
        layout.addWidget(upload_date)
        
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Update the stylesheet to use proper Qt properties
        self.setStyleSheet("""
            QWidget {
                background-color: #3b3b3b;
                border-radius: 8px;
            }
            QWidget:hover {
                background-color: #454545;
            }
        """)
        
        # Set cursor shape directly instead of using CSS
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Adjust card size to accommodate thumbnail
        self.setMinimumSize(340, 320)
        self.setMaximumSize(340, 320)
        
        # Add remove button at the bottom
        remove_button = QPushButton("Remove Channel")
        remove_button.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                padding: 5px;
                border-radius: 4px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        remove_button.clicked.connect(self.remove_channel)
        layout.addWidget(remove_button)
        
        self.setLayout(layout)
        self.clicked.connect(self.open_video)
        self.setMouseTracking(True)
        
    def load_thumbnail(self, video_id):
        try:
            # Use requests to download the thumbnail
            url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8"
            }
            response = requests.get(url, headers=headers, verify=True)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Create QPixmap from the downloaded data
            pixmap = QPixmap()
            if pixmap.loadFromData(response.content):
                scaled_pixmap = pixmap.scaled(
                    self.thumbnail.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.thumbnail.setPixmap(scaled_pixmap)
                print(f"Successfully loaded thumbnail for video {video_id}")
            else:
                print(f"Failed to create pixmap from thumbnail data for video {video_id}")
                
        except Exception as e:
            print(f"Error loading thumbnail for video {video_id}: {str(e)}")
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            
    def open_video(self):
        video_url = f"https://www.youtube.com/watch?v={self.video_data['video_id']}"
        webbrowser.open(video_url)

    def remove_channel(self):
        try:
            # Remove from database
            self.parent.db.remove_channel(self.video_data['channel_id'])
            # Reload the channels display
            asyncio.create_task(self.parent.load_channels())
        except Exception as e:
            print(f"Error removing channel: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Channel Tracker")
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create search section
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search YouTube Channel")
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(lambda: asyncio.create_task(self.search_channel()))
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        main_layout.addLayout(search_layout)

        # Add Update All Channels button
        self.update_button = QPushButton("Update All Channels")
        self.update_button.clicked.connect(lambda: asyncio.create_task(self.update_all_channels()))
        main_layout.addWidget(self.update_button)

        # Create scrollable grid for channel videos
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.grid_layout = QGridLayout(scroll_content)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # Initialize database
        self.db = Database()
        
        # Load existing channels
        # asyncio.create_task(self.load_channels())

    async def search_channel(self):
        query = self.search_input.text()
        if not query:
            return

        try:
            print(f"Searching for channel: {query}")
            channels = Search.channels(query, 3)  # Get top 3 channels
            if not channels:
                print("No channels found")
                return

            search_results = []
            for channel_id in channels:
                try:
                    channel = Channel(channel_id)
                    metadata = channel.metadata
                    print(metadata)
                    
                    search_result = {
                        'channel_id': channel_id,
                        'name': metadata.get('name', 'Unknown Channel'),
                        'subscribers': str(metadata.get('subscribers', 'N/A')),
                        'description': metadata.get('description', 'No description available'),
                        'avatar': metadata.get('avatar', '')
                    }
                    search_results.append(search_result)
                except Exception as channel_error:
                    print(f"Error fetching channel {channel_id}: {channel_error}")

            print(f"Found channels: {search_results}")
            
            self.channel_info_window = ChannelInfoWindow(search_results, self)
            self.channel_info_window.show()
            
        except Exception as e:
            print(f"Search error: {str(e)}")

    async def load_channels(self):
        # Clear existing grid
        for i in reversed(range(self.grid_layout.count())): 
            self.grid_layout.itemAt(i).widget().setParent(None)
        
        # Get channels from database
        channels = self.db.get_all_channels()
        print(f"Loaded channels from database: {channels}")
        
        # Add channels to grid
        row = 0
        col = 0
        max_cols = 3
        
        # Set larger spacing between cards
        self.grid_layout.setSpacing(30)
        self.grid_layout.setContentsMargins(30, 30, 30, 30)
        
        for channel in channels:
            video_data = {
                'channel_name': channel[1],
                'channel_id': channel[2],
                'video_id': channel[3],
                'video_title': channel[4],
                'video_views': channel[5],
                'upload_date': channel[6],
            }
            
            video_card = VideoCard(video_data, self)
            self.grid_layout.addWidget(video_card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    async def update_all_channels(self):
        try:
            channels = self.db.get_all_channels()
            updated_channels = []
            no_updates = []
            
            for channel in channels:
                channel_id = channel[2]
                channel_name = channel[1]
                
                # Get channel and latest video data
                channel_obj = Channel(channel_id)
                latest_video_id = channel_obj.last_uploaded()
                
                if latest_video_id and latest_video_id != channel[3]:
                    # Get new video details
                    video = Video(latest_video_id)
                    video_metadata = video.metadata
                    
                    # Update channel data
                    channel_data = {
                        'channel_name': channel_name,
                        'channel_id': channel_id,
                        'video_id': latest_video_id,
                        'video_title': video_metadata.get('title', 'Video information unavailable'),
                        'video_views': str(video_metadata.get('views', 'N/A')),
                        'upload_date': str(video_metadata.get('upload_date', 'N/A'))
                    }
                    
                    # Update in database
                    self.db.update_channel(channel_data)
                    updated_channels.append(channel_name)
                else:
                    no_updates.append(channel_name)
            
            # Print update summary
            if updated_channels:
                print("\nChannels updated with new videos:")
                for name in updated_channels:
                    print(f"✓ {name}")
            
            if no_updates:
                print("\nChannels with no new videos:")
                for name in no_updates:
                    print(f"- {name}")
                    
            if not channels:
                print("\nNo channels in database to update!")
            
            # Reload the channel display
            await self.load_channels()
            
        except Exception as e:
            print(f"Error updating channels: {str(e)}")

async def main():
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = MainWindow()
    await window.load_channels()
    window.show()

    # Create periodic update task
    async def periodic_update():
        while True:
            try:
                await asyncio.sleep(3600)  # Check for updates every hour
                await window.update_all_channels()
            except Exception as e:
                pass
                # print(f"Error in periodic update: {e}")

    # Start periodic update
    asyncio.create_task(periodic_update())
    
    # Run the event loop
    try:
        await loop.run_forever()
    finally:
        loop.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nApplication closed by user")
