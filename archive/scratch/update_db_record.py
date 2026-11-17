import sqlite3

conn = sqlite3.connect('data/posts.db')
c = conn.cursor()
c.execute(
    "UPDATE blog_posts SET file_path = ?, updated_at = datetime('now') WHERE id = ?",
    ('posts/naver_solidlog_01_monthly_rent.md', 98)
)
conn.commit()

c.execute("SELECT id, blog_id, title, file_path, status FROM blog_posts WHERE id = 98")
row = c.fetchone()
print("Updated Row:", row)
conn.close()
