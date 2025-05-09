# PokeVin - Pokemon Price Tracker

Web-scraping tool that fetches Pokemon card prices. It uses PlayWright to scrape import metric such as price/title/source and stores them in a SQLite database via Django. 

## Features

- Scrapes eBay for Pokémon card prices and details
- Stores the data in a Django model for easy management
- Displays the scraped data in Django Admin

# Installation steps
**Clone the repository:**
```
git clone https://github.com/VinPal5554/PokeVin.git
cd PokeVin\PokeVin_Backend
```

**Setup Virtual Environment:**
```
python -m venv venv
venv\Scripts\activate
```

**Install dependencies:**
```
pip install django playwright psycopg2 decimal requests
python -m playwright install
```

**Setup SQLite database:**
```
python manage.py migrate
```

**Setup Django Admin:**
```
python manage.py createsuperuser
```

**Run Django Dev Server:**
```
python manage.py runserver
```
