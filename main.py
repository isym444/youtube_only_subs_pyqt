import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLineEdit, QPushButton, QGridLayout, 
                            QLabel, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QTimer
import asyncio
import aiotube
from database import Database
import qasync

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
            
            # Display channel info
            channel_name = QLabel(f"Channel: {channel_data['name']}")
            subscribers = QLabel(f"Subscribers: {channel_data['subscribers']}")
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
            channel = aiotube.Channel(channel_data['channel_id'])
            metadata = channel.metadata
            
            # Get latest video
            latest_video_id = channel.last_uploaded()
            if not latest_video_id:
                print("Could not fetch latest video ID")
                return

            print(f"Latest video ID: {latest_video_id}")
            
            try:
                # Get video details
                video = aiotube.Video(latest_video_id)
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
    def __init__(self, video_data, parent=None):
        super().__init__()
        layout = QVBoxLayout()
        
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
        
        # Add widgets to layout with some spacing
        layout.addWidget(channel_name)
        layout.addWidget(video_title)
        layout.addWidget(video_views)
        layout.addWidget(upload_date)
        
        # Remove spacing between widgets
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Style the card
        self.setStyleSheet("""
            QWidget {
                background-color: #3b3b3b;
                border-radius: 8px;
            }
        """)
        
        # Set a fixed size for the card
        self.setMinimumSize(300, 150)
        self.setMaximumSize(400, 200)
        
        self.setLayout(layout)

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
            channels = aiotube.Search.channels(query, 3)  # Get top 3 channels
            if not channels:
                print("No channels found")
                return

            search_results = []
            for channel_id in channels:
                try:
                    channel = aiotube.Channel(channel_id)
                    metadata = channel.metadata
                    
                    search_result = {
                        'channel_id': channel_id,
                        'name': metadata.get('name', 'Unknown Channel'),
                        'subscribers': str(metadata.get('subscriber_count', 'N/A')),
                        'description': metadata.get('description', 'No description available')
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
        
        # Set spacing between cards
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)
        
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
            await asyncio.sleep(3600)  # Check for updates every hour
            await window.update_all_channels()

    # Start periodic update
    asyncio.create_task(periodic_update())
    
    # Run the event loop
    with loop:
        await loop.run_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nApplication closed by user")
