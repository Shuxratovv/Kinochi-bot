import sqlite3
import logging

DB_NAME = "kinochi.db"

logger = logging.getLogger(__name__)


# ==================================================
# DATABASE CONNECTION
# ==================================================

def get_connection():

    conn = sqlite3.connect(DB_NAME)

    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# ==================================================
# DATABASE YARATISH / YANGILASH
# ==================================================

def create_database():

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        # ==================================================
        # USERS
        # ==================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ==================================================
        # MOVIES
        # ==================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                code TEXT UNIQUE
            )
        """)

        # ==================================================
        # EPOCHES
        # ==================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                movie_id INTEGER NOT NULL,
                season INTEGER NOT NULL,
                episode INTEGER NOT NULL,
                file_id TEXT NOT NULL,

                FOREIGN KEY (movie_id)
                REFERENCES movies(id)
                ON DELETE CASCADE,

                UNIQUE(movie_id, season, episode)
            )
        """)

        # ==================================================
        # FAVORITES
        # ==================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,
                movie_id INTEGER NOT NULL,

                UNIQUE(user_id, movie_id),

                FOREIGN KEY (movie_id)
                REFERENCES movies(id)
                ON DELETE CASCADE
            )
        """)

        conn.commit()

        # ==================================================
        # ESKI DATABASE MIGRATION
        # ==================================================

        cursor.execute("PRAGMA table_info(movies)")

        columns = [
            row[1]
            for row in cursor.fetchall()
        ]

        # Eski movies jadvalida code bo'lmasa
        if "code" not in columns:

            logger.info(
                "Eski database aniqlandi. 'code' ustuni qo'shilmoqda."
            )

            cursor.execute(
                "ALTER TABLE movies ADD COLUMN code TEXT"
            )

            conn.commit()

        # ==================================================
        # ESKI KINOLARGA CODE BERISH
        # ==================================================

        cursor.execute("""
            SELECT id
            FROM movies
            WHERE code IS NULL
            ORDER BY id
        """)

        old_movies = cursor.fetchall()

        for row in old_movies:

            movie_id = row[0]

            cursor.execute("""
                UPDATE movies
                SET code = ?
                WHERE id = ?
            """, (
                str(movie_id),
                movie_id
            ))

        conn.commit()

        # ==================================================
        # CODE UNIQUE INDEX
        # ==================================================

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_movies_code
            ON movies(code)
        """)

        conn.commit()

        logger.info(
            "Database muvaffaqiyatli yaratildi/yangilandi."
        )

    except sqlite3.Error:

        logger.exception(
            "Database yaratishda/yangilashda xatolik."
        )

        if conn:
            conn.rollback()

        raise

    finally:

        if conn:
            conn.close()


# ==================================================
# USER QO'SHISH
# ==================================================

def add_user(user_id):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO users
            (user_id)
            VALUES (?)
        """, (user_id,))

        conn.commit()

        return True

    except sqlite3.Error:

        logger.exception(
            "Foydalanuvchini saqlashda xatolik."
        )

        if conn:
            conn.rollback()

        return False

    finally:

        if conn:
            conn.close()


# ==================================================
# KINO QO'SHISH
# ==================================================

def add_movie(
    title,
    code
):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO movies
            (
                title,
                code
            )
            VALUES (?, ?)
        """, (
            title,
            code
        ))

        movie_id = cursor.lastrowid

        conn.commit()

        return movie_id

    except sqlite3.IntegrityError:

        if conn:
            conn.rollback()

        logger.warning(
            "Kino qo'shilmadi. Kod band: %s",
            code
        )

        return None

    except sqlite3.Error:

        logger.exception(
            "Kino qo'shishda database xatosi."
        )

        if conn:
            conn.rollback()

        return None

    finally:

        if conn:
            conn.close()


# ==================================================
# KINO KOD BO'YICHA OLISH
# ==================================================

def get_movie_by_code(code):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, code
            FROM movies
            WHERE code = ?
        """, (str(code).strip(),))

        return cursor.fetchone()

    except sqlite3.Error:

        logger.exception(
            "Kino kod bo'yicha qidirishda xatolik."
        )

        return None

    finally:

        if conn:
            conn.close()


# ==================================================
# KINO NOMI BO'YICHA QIDIRISH
# ==================================================

def search_movies(query):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        query = query.strip()

        cursor.execute("""
            SELECT id, title, code
            FROM movies
            WHERE title LIKE ? COLLATE NOCASE
            ORDER BY title
        """, (
            f"%{query}%",
        ))

        return cursor.fetchall()

    except sqlite3.Error:

        logger.exception(
            "Kino qidirishda database xatosi."
        )

        return []

    finally:

        if conn:
            conn.close()


# ==================================================
# BARCHA KINOLAR
# ==================================================

def get_all_movies():

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, code
            FROM movies
            ORDER BY title
        """)

        return cursor.fetchall()

    except sqlite3.Error:

        logger.exception(
            "Kinolarni olishda database xatosi."
        )

        return []

    finally:

        if conn:
            conn.close()


# ==================================================
# BIRTA KINO
# ==================================================

def get_movie(movie_id):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, code
            FROM movies
            WHERE id = ?
        """, (
            movie_id,
        ))

        return cursor.fetchone()

    except sqlite3.Error:

        logger.exception(
            "Kino olishda database xatosi."
        )

        return None

    finally:

        if conn:
            conn.close()


# ==================================================
# KINO NOMINI TAHRIRLASH
# ==================================================

def update_movie_title(
    movie_id,
    new_title
):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE movies
            SET title = ?
            WHERE id = ?
        """, (
            new_title.strip(),
            movie_id
        ))

        if cursor.rowcount == 0:

            conn.rollback()

            return False

        conn.commit()

        return True

    except sqlite3.IntegrityError:

        if conn:
            conn.rollback()

        logger.warning(
            "Kino nomi bilan bog'liq xatolik."
        )

        return False

    except sqlite3.Error:

        logger.exception(
            "Kino nomini tahrirlashda xatolik."
        )

        if conn:
            conn.rollback()

        return False

    finally:

        if conn:
            conn.close()


# ==================================================
# KINO KODINI TAHRIRLASH
# ==================================================

def update_movie_code(
    movie_id,
    new_code
):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE movies
            SET code = ?
            WHERE id = ?
        """, (
            new_code.strip(),
            movie_id
        ))

        if cursor.rowcount == 0:

            conn.rollback()

            return False

        conn.commit()

        return True

    except sqlite3.IntegrityError:

        if conn:
            conn.rollback()

        logger.warning(
            "Yangi kod allaqachon mavjud: %s",
            new_code
        )

        return False

    except sqlite3.Error:

        logger.exception(
            "Kino kodini tahrirlashda xatolik."
        )

        if conn:
            conn.rollback()

        return False

    finally:

        if conn:
            conn.close()


# ==================================================
# KINO O'CHIRISH
# ==================================================

def delete_movie(movie_id):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        # Avval kinoning barcha qismlarini o'chiramiz
        cursor.execute(
            """
            DELETE FROM episodes
            WHERE movie_id = ?
            """,
            (movie_id,)
        )

        # Keyin sevimlilarni o'chiramiz
        cursor.execute(
            """
            DELETE FROM favorites
            WHERE movie_id = ?
            """,
            (movie_id,)
        )

        # Oxirida kinoning o'zini o'chiramiz
        cursor.execute(
            """
            DELETE FROM movies
            WHERE id = ?
            """,
            (movie_id,)
        )

        if cursor.rowcount == 0:

            conn.rollback()

            return False

        conn.commit()

        logger.info(
            "Kino o'chirildi: movie_id=%s",
            movie_id
        )

        return True

    except sqlite3.Error:

        if conn:
            conn.rollback()

        logger.exception(
            "Kino o'chirishda database xatosi."
        )

        return False

    finally:

        if conn:
            conn.close()


# ==================================================
# QISM SAQLASH
# ==================================================

def add_episode(
    movie_id,
    season,
    episode,
    file_id
):
    """Qismni saqlaydi yoki shu qism mavjud bo'lsa file_id ni yangilaydi.

    Bu funksiya eski kinochi.db bazalarida episodes jadvalida
    UNIQUE(movie_id, season, episode) constraint bo'lmagan holatda ham
    ishlaydi. Shuning uchun eski database sababli ommaviy yuklash
    to'xtab qolmaydi.
    """

    conn = None

    try:
        if not movie_id or not season or not episode or not file_id:
            logger.warning(
                "Qism saqlanmadi: noto'g'ri ma'lumot movie_id=%r season=%r episode=%r file_id mavjud=%s",
                movie_id, season, episode, bool(file_id)
            )
            return False

        conn = get_connection()
        cursor = conn.cursor()

        # Avval mavjud qismni yangilaymiz.
        # Bu eski database'lardagi UNIQUE constraintga bog'liq emas.
        cursor.execute(
            """
            UPDATE episodes
            SET file_id = ?
            WHERE movie_id = ?
              AND season = ?
              AND episode = ?
            """,
            (file_id, movie_id, season, episode)
        )

        if cursor.rowcount == 0:
            # Qism hali mavjud emas — yangi qism sifatida qo'shamiz.
            cursor.execute(
                """
                INSERT INTO episodes
                (movie_id, season, episode, file_id)
                VALUES (?, ?, ?, ?)
                """,
                (movie_id, season, episode, file_id)
            )

        conn.commit()

        logger.info(
            "Qism saqlandi: movie_id=%s season=%s episode=%s",
            movie_id, season, episode
        )

        return True

    except sqlite3.Error:
        logger.exception(
            "Qism saqlashda database xatosi: movie_id=%s season=%s episode=%s",
            movie_id, season, episode
        )

        if conn:
            conn.rollback()

        return False

    finally:
        if conn:
            conn.close()


# ==================================================
# FASLLARNI OLISH
# ==================================================

def get_seasons(movie_id):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT season
            FROM episodes
            WHERE movie_id = ?
            ORDER BY season
        """, (
            movie_id,
        ))

        results = cursor.fetchall()

        return [
            row[0]
            for row in results
        ]

    except sqlite3.Error:

        logger.exception(
            "Fasllarni olishda xatolik."
        )

        return []

    finally:

        if conn:
            conn.close()


# ==================================================
# QISMLARNI OLISH
# ==================================================

def get_episodes(
    movie_id,
    season
):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT episode
            FROM episodes
            WHERE movie_id = ?
            AND season = ?
            ORDER BY episode
        """, (
            movie_id,
            season
        ))

        results = cursor.fetchall()

        return [
            row[0]
            for row in results
        ]

    except sqlite3.Error:

        logger.exception(
            "Qismlarni olishda xatolik."
        )

        return []

    finally:

        if conn:
            conn.close()


# ==================================================
# BIRTA QISM
# ==================================================

def get_episode(
    movie_id,
    season,
    episode
):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT file_id
            FROM episodes
            WHERE movie_id = ?
            AND season = ?
            AND episode = ?
        """, (
            movie_id,
            season,
            episode
        ))

        result = cursor.fetchone()

        if result:

            return result[0]

        return None

    except sqlite3.Error:

        logger.exception(
            "Qism videosini olishda xatolik."
        )

        return None

    finally:

        if conn:
            conn.close()


# ==================================================
# QISM O'CHIRISH
# ==================================================

def delete_episode(
    movie_id,
    season,
    episode
):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM episodes
            WHERE movie_id = ?
            AND season = ?
            AND episode = ?
        """, (
            movie_id,
            season,
            episode
        ))

        if cursor.rowcount == 0:

            conn.rollback()

            return False

        conn.commit()

        return True

    except sqlite3.Error:

        logger.exception(
            "Qism o'chirishda xatolik."
        )

        if conn:
            conn.rollback()

        return False

    finally:

        if conn:
            conn.close()


# ==================================================
# FASL O'CHIRISH
# ==================================================

def delete_season(
    movie_id,
    season
):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM episodes
            WHERE movie_id = ?
            AND season = ?
        """, (
            movie_id,
            season
        ))

        if cursor.rowcount == 0:

            conn.rollback()

            return False

        conn.commit()

        return True

    except sqlite3.Error:

        logger.exception(
            "Fasl o'chirishda xatolik."
        )

        if conn:
            conn.rollback()

        return False

    finally:

        if conn:
            conn.close()


# ==================================================
# SEVIMLIGA QO'SHISH
# ==================================================

def add_favorite(
    user_id,
    movie_id
):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO favorites
            (
                user_id,
                movie_id
            )
            VALUES (?, ?)
        """, (
            user_id,
            movie_id
        ))

        conn.commit()

        return True

    except sqlite3.Error:

        logger.exception(
            "Sevimliga qo'shishda xatolik."
        )

        if conn:
            conn.rollback()

        return False

    finally:

        if conn:
            conn.close()


# ==================================================
# SEVIMLIDAN OLIB TASHLASH
# ==================================================

def remove_favorite(
    user_id,
    movie_id
):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM favorites
            WHERE user_id = ?
            AND movie_id = ?
        """, (
            user_id,
            movie_id
        ))

        conn.commit()

        return True

    except sqlite3.Error:

        logger.exception(
            "Sevimlidan olib tashlashda xatolik."
        )

        if conn:
            conn.rollback()

        return False

    finally:

        if conn:
            conn.close()


# ==================================================
# SEVIMLILIGINI TEKSHIRISH
# ==================================================

def is_favorite(
    user_id,
    movie_id
):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id
            FROM favorites
            WHERE user_id = ?
            AND movie_id = ?
        """, (
            user_id,
            movie_id
        ))

        return cursor.fetchone() is not None

    except sqlite3.Error:

        logger.exception(
            "Sevimliligini tekshirishda xatolik."
        )

        return False

    finally:

        if conn:
            conn.close()


# ==================================================
# SEVIMLILARNI OLISH
# ==================================================

def get_favorites(user_id):

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                movies.id,
                movies.title,
                movies.code
            FROM favorites

            INNER JOIN movies
            ON favorites.movie_id = movies.id

            WHERE favorites.user_id = ?

            ORDER BY movies.title
        """, (
            user_id,
        ))

        return cursor.fetchall()

    except sqlite3.Error:

        logger.exception(
            "Sevimlilarni olishda xatolik."
        )

        return []

    finally:

        if conn:
            conn.close()


# ==================================================
# UMUMIY STATISTIKA
# ==================================================

def get_statistics():

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        # USERS

        cursor.execute(
            "SELECT COUNT(*) FROM users"
        )

        user_count = cursor.fetchone()[0]

        # MOVIES

        cursor.execute(
            "SELECT COUNT(*) FROM movies"
        )

        movie_count = cursor.fetchone()[0]

        # EPISODES

        cursor.execute(
            "SELECT COUNT(*) FROM episodes"
        )

        episode_count = cursor.fetchone()[0]

        return (
            user_count,
            movie_count,
            episode_count
        )

    except sqlite3.Error:

        logger.exception(
            "Statistikani olishda xatolik."
        )

        return (
            0,
            0,
            0
        )

    finally:

        if conn:
            conn.close()


# ==================================================
# JAMI SEVIMLILAR
# ==================================================

def get_favorite_count():

    conn = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM favorites
            """
        )

        return cursor.fetchone()[0]

    except sqlite3.Error:

        logger.exception(
            "Sevimlilar statistikasini olishda xatolik."
        )

        return 0

    finally:

        if conn:
            conn.close()