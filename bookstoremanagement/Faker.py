import random
import json
from faker import Faker

fake = Faker()

def generate_book(index):
    return {
        "name": f"Sách {index} - {fake.word().capitalize()}",
        "price": random.randint(30000, 100000),
        "publisherName": fake.name(),
        "image": 'https://res.cloudinary.com/dzwsdpjgi/image/upload/v1734358631/images_ejbach.jpg',
        "description": fake.sentence(),
        "quantity": random.randint(50, 200),
        "category_id": random.randint(1, 15)
    }

books = [generate_book(i) for i in range(1, 1001)]

# Save to a JSON file
with open('bookstoremanagement/data/books.json', 'w', encoding='utf-8') as f:
    json.dump(books, f, ensure_ascii=False, indent=4)

print(f"Đã tạo {len(books)} cuốn sách!")
