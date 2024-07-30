import sys
import os
import requests
import json
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, 
                             QTextBrowser, QLabel, QComboBox, QScrollArea, QStatusBar, QFileDialog,
                             QTabWidget, QSpinBox, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl, QSettings
from PyQt5.QtGui import QDesktopServices

class Config:
    def __init__(self):
        self.settings = QSettings('NewsApp', 'NewsFecher')
        self.api_key = self.settings.value('api_key', '')

    def save_api_key(self, api_key):
        self.api_key = api_key
        self.settings.setValue('api_key', api_key)

class NewsFetcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2/"

    def fetch_top_headlines(self, country="us", category=None, page_size=5, page=1):
        endpoint = f"{self.base_url}top-headlines"
        params = {
            "apiKey": self.api_key,
            "country": country,
            "pageSize": page_size,
            "page": page
        }
        if category and category != "":
            params["category"] = category

        response = requests.get(endpoint, params=params)
        return response.json()

    def fetch_everything(self, query, from_date=None, to_date=None, language="en", sort_by="publishedAt", page_size=5, page=1):
        endpoint = f"{self.base_url}everything"
        if from_date is None:
            from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        if to_date is None:
            to_date = datetime.now().strftime('%Y-%m-%d')

        params = {
            "apiKey": self.api_key,
            "q": query,
            "from": from_date,
            "to": to_date,
            "language": language,
            "sortBy": sort_by,
            "pageSize": page_size,
            "page": page
        }

        response = requests.get(endpoint, params=params)
        return response.json()

class FetchThread(QThread):
    result_ready = pyqtSignal(object)
    
    def __init__(self, fetcher, method, *args, **kwargs):
        super().__init__()
        self.fetcher = fetcher
        self.method = method
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        result = getattr(self.fetcher, self.method)(*self.args, **self.kwargs)
        self.result_ready.emit(result)

class NewsApp(QWidget):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.news_fetcher = NewsFetcher(self.config.api_key)
        self.current_page = 1
        self.total_results = 0
        self.current_method = None
        self.current_params = {}
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # API Key Input
        api_key_layout = QHBoxLayout()
        self.api_key_input = QLineEdit(self.config.api_key)
        self.api_key_input.setPlaceholderText("Enter your NewsAPI key")
        api_key_layout.addWidget(self.api_key_input)
        save_api_key_btn = QPushButton("Save API Key")
        save_api_key_btn.clicked.connect(self.save_api_key)
        api_key_layout.addWidget(save_api_key_btn)
        layout.addLayout(api_key_layout)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_headlines_tab(), "Top Headlines")
        self.tabs.addTab(self.create_search_tab(), "Search News")
        layout.addWidget(self.tabs)

        # Results Area
        self.results_area = QTextBrowser()
        self.results_area.setOpenExternalLinks(True)
        self.results_area.anchorClicked.connect(self.open_link)
        
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.results_area)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # Pagination
        pagination_layout = QHBoxLayout()
        self.prev_btn = QPushButton("Previous")
        self.prev_btn.clicked.connect(self.prev_page)
        self.prev_btn.setEnabled(False)
        pagination_layout.addWidget(self.prev_btn)

        self.page_label = QLabel("Page 1")
        pagination_layout.addWidget(self.page_label)

        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self.next_page)
        self.next_btn.setEnabled(False)
        pagination_layout.addWidget(self.next_btn)

        layout.addLayout(pagination_layout)

        # Save to File Button
        save_btn = QPushButton("Save to File")
        save_btn.clicked.connect(self.save_to_file)
        layout.addWidget(save_btn)

        # Status Bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)

        self.setLayout(layout)
        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle('News Fetcher')
        self.show()

    def create_headlines_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        top_headlines_layout = QHBoxLayout()
        self.country_input = QLineEdit()
        self.country_input.setPlaceholderText("Country code (e.g., us, gb)")
        top_headlines_layout.addWidget(self.country_input)
        
        self.category_combo = QComboBox()
        self.category_combo.addItems(["", "business", "entertainment", "general", "health", "science", "sports", "technology"])
        top_headlines_layout.addWidget(self.category_combo)
        
        fetch_headlines_btn = QPushButton("Fetch Headlines")
        fetch_headlines_btn.clicked.connect(self.fetch_headlines)
        top_headlines_layout.addWidget(fetch_headlines_btn)
        
        layout.addLayout(top_headlines_layout)
        tab.setLayout(layout)
        return tab

    def create_search_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search query")
        search_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.search_news)
        search_layout.addWidget(search_btn)
        
        layout.addLayout(search_layout)
        tab.setLayout(layout)
        return tab

    def save_api_key(self):
        api_key = self.api_key_input.text()
        self.config.save_api_key(api_key)
        self.news_fetcher.api_key = api_key
        QMessageBox.information(self, "API Key", "API Key saved successfully!")

    def fetch_headlines(self):
        country = self.country_input.text() or "us"
        category = self.category_combo.currentText()
        self.status_bar.showMessage("Fetching headlines...")
        self.current_method = "fetch_top_headlines"
        self.current_params = {"country": country, "category": category}
        self.current_page = 1
        self.fetch_thread = FetchThread(self.news_fetcher, self.current_method, **self.current_params, page=self.current_page)
        self.fetch_thread.result_ready.connect(self.on_fetch_complete)
        self.fetch_thread.start()

    def search_news(self):
        query = self.search_input.text()
        if query:
            self.status_bar.showMessage("Searching news...")
            self.current_method = "fetch_everything"
            self.current_params = {"query": query}
            self.current_page = 1
            self.fetch_thread = FetchThread(self.news_fetcher, self.current_method, **self.current_params, page=self.current_page)
            self.fetch_thread.result_ready.connect(self.on_fetch_complete)
            self.fetch_thread.start()
        else:
            self.results_area.setHtml("Please enter a search query.")

    def on_fetch_complete(self, result):
        if 'articles' in result:
            self.display_articles(result['articles'])
            self.total_results = result.get('totalResults', 0)
            self.update_pagination()
            self.status_bar.showMessage(f"Fetch complete. Total results: {self.total_results}", 3000)
        else:
            error_message = result.get('message', 'An unknown error occurred.')
            self.results_area.setHtml(f"<p style='color: red;'>Error: {error_message}</p>")
            self.status_bar.showMessage("Error occurred", 3000)

    def display_articles(self, articles):
        if not articles:
            self.results_area.setHtml("<p>No articles found.</p>")
            return

        display_text = ""
        for i, article in enumerate(articles, 1):
            display_text += f"<h3>{i}. <a href='{article['url']}'>{article['title']}</a></h3>"
            display_text += f"<p><strong>Source:</strong> {article['source']['name']}<br>"
            display_text += f"<strong>Published:</strong> {article['publishedAt']}<br>"
            display_text += f"<strong>Description:</strong> {article['description']}</p>"
            display_text += "<hr>"
        self.results_area.setHtml(display_text)

    def open_link(self, url):
        QDesktopServices.openUrl(url)

    def save_to_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Articles", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(self.results_area.toPlainText())
            self.status_bar.showMessage(f"Saved to {file_path}", 3000)

    def update_pagination(self):
        self.page_label.setText(f"Page {self.current_page}")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page * 20 < self.total_results)

    def next_page(self):
        self.current_page += 1
        self.fetch_thread = FetchThread(self.news_fetcher, self.current_method, **self.current_params, page=self.current_page)
        self.fetch_thread.result_ready.connect(self.on_fetch_complete)
        self.fetch_thread.start()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.fetch_thread = FetchThread(self.news_fetcher, self.current_method, **self.current_params, page=self.current_page)
            self.fetch_thread.result_ready.connect(self.on_fetch_complete)
            self.fetch_thread.start()

def main():
    app = QApplication(sys.argv)
    ex = NewsApp()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
