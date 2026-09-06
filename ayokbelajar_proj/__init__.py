"""Pakai PyMySQL sebagai fallback MySQLdb murni-Python.

VPS/shared hosting: `mysqlclient` (biner, cepat) tetap prioritas.
Vercel serverless: tidak ada libmysqlclient sistem → `mysqlclient` gagal build,
maka `pymysql.install_as_MySQLdb()` memungkinkan Django backend `mysql` jalan
tanpa compiler. Aman di semua hosting karena hanya aktif bila `pymysql` terinstall.
"""
try:
    import pymysql  # type: ignore

    pymysql.install_as_MySQLdb()
except ImportError:
    pass
