import mariadb

conn = mariadb.connect(
    host="ltop.kr",
    port=43306,
    user="ltop",
    password="dpfxkq123$%^",
    database="cathodic_protection"
)

try:
    cursor = conn.cursor()

    sql = """
        INSERT INTO stat_pre_tb (
            equip_id,
            bettery,
            inner_temp,
            corrol_volt,
            inner_humidity
        )
        VALUES (?, ?, ?, ?, ?)
    """

    data = (
        "TB001",   # equip_id
        3.7,       # bettery
        25.4,      # inner_temp
        -920.5,    # corrol_volt
        55.2       # inner_humidity
    )

    cursor.execute(sql, data)
    conn.commit()

    print("DB INSERT 성공")
    print("생성된 t_no:", cursor.lastrowid)

except mariadb.Error as e:
    conn.rollback()
    print("DB INSERT 실패:", e)

finally:
    conn.close()