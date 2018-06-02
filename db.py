import pymysql
from config import mysql_config

queries = {
    "drop_table": "DROP TABLE ACM_WC;",
    "create_table": """
                      CREATE TABLE IF NOT EXISTS ACM_WC
                      ( id smallint unsigned not null auto_increment,
                      first_name VARCHAR(25) not null,
                      surname VARCHAR(25) not null,
                      email VARCHAR(40) not null,
                      password TEXT(256) not NULL,
                      confirmed BOOLEAN NOT NULL,
                      confirmation_token VARCHAR(20),
                      password_forgot_token VARCHAR(20),
                      file_submitted VARCHAR (100),
                      constraint pk primary key (id));""",
    "check_user_exists": """SELECT email FROM ACM_WC WHERE email=%s;""",
    "create_user": """INSERT INTO ACM_WC (
                      first_name, 
                      surname, 
                      email,
                      password,
                      confirmed,
                      confirmation_token)
                      VALUES (%s, %s, %s, %s, FALSE, %s)""",
    "id_from_confirmation_token": """SELECT id FROM ACM_WC WHERE confirmation_token=%s""",
    "confirm_user": """UPDATE ACM_WC
                        SET confirmation_token=NULL, confirmed=TRUE 
                        WHERE id=%s""",
    "get_user": """SELECT * FROM ACM_WC WHERE email=%s""",
    "delete_user": """DELETE FROM ACM_WC WHERE email=%s""",
    "change_password": """UPDATE ACM_WC
                          SET password_forgot_token=NULL, password=%s
                          WHERE password_forgot_token=%s;""",
    "add_change_password_token": """UPDATE ACM_WC
                                    SET password_forgot_token=%s
                                    WHERE email=%s;""",
    "add_confirmation_token": """UPDATE ACM_WC
                                 SET confirmation_token=%s
                                  WHERE email=%s;""",
    "add_file_submitted": """UPDATE ACM_WC
                            SET file_submitted=%s
                            WHERE email=%s;""",
    "delete_file_submitted": """UPDATE ACM_WC
                                SET file_submitted=NULL 
                                WHERE email=%s;""",
}


class FailedToCreateTable(Exception):
    pass


class FailedToCheckUserAlreadyExists(Exception):
    pass


class FailedToCreateUser(Exception):
    pass


class TokenDoesNotExist(Exception):
    pass


class FailedToConfirmUser(Exception):
    pass


class UserDoesNotExist(Exception):
    pass


class FailedToRetrieveUser(Exception):
    pass


class FailedToDeleteUser(Exception):
    pass


class UserExists(Exception):
    pass


class FailedToAddChangePasswordToken(Exception):
    pass


class FailedToChangePassword(Exception):
    pass


class FailedToAddConfirmationToken(Exception):
    pass


class FailedToAddFile(Exception):
    pass


class FailedToRemoveFileEntry(Exception):
    pass


def _connection():
    return pymysql.connect(**mysql_config['connection'])


def drop_table():
    con = _connection()
    try:
        with con.cursor() as cursor:
            cursor.execute(queries["drop_table"])
            con.commit()
    except Exception:
        raise FailedToCreateTable("Failed To drop Table")
    finally:
        con.close()


def create_table():
    con = _connection()
    try:
        with con.cursor() as cursor:
            cursor.execute(queries["create_table"])
            con.commit()
    except Exception:
        raise FailedToCreateTable("Failed To Create Table")
    finally:
        con.close()


def user_exists(email):
    con = _connection()
    _user_exists = False
    try:
        with con.cursor() as cursor:
            cursor.execute(queries["check_user_exists"], email)
            if cursor.rowcount:
                _user_exists = True
        con.commit()
        con.close()
        return _user_exists
    except Exception:
        raise FailedToCheckUserAlreadyExists("Failed To Check User Already Exists")


def is_confirmed(email):
    user = get_user_with_email(email)
    return user["confirmed"]


def create_user(first_name, surname, email, password, confirmation_token):
    con = _connection()
    try:
        if not user_exists(email):
            try:
                with con.cursor() as cursor:
                    cursor.execute(queries["create_user"], (first_name, surname, email, password, confirmation_token))
                    con.commit()
            except Exception:
                raise FailedToCreateUser("Failed To Create User")
        else:
            raise UserExists("User Already Exists")
    except Exception as e:
        raise e
    finally:
        con.close()


def confirm_token(confirmation_token):
    con = _connection()
    try:
        with con.cursor() as cursor:
            cursor.execute(queries["id_from_confirmation_token"], confirmation_token)
            if not cursor.rowcount:
                raise TokenDoesNotExist("Confirmation Token Does Not Exist")
            user_id = cursor.fetchone()['id']
            cursor.execute(queries["confirm_user"], user_id)
            con.commit()
    except Exception:
        raise FailedToConfirmUser("Failed To Confirm User")
    finally:
        con.close()


def get_user_with_email(email):
    try:
        if user_exists(email):
            con = _connection()
            try:
                with con.cursor() as cursor:
                    cursor.execute(queries["get_user"], email)
                    if not cursor.rowcount:
                        raise UserDoesNotExist("User Does Not Exist")
                    con.commit()
                    con.close()
                    return cursor.fetchone()
            except Exception:
                raise FailedToRetrieveUser("Failed To Retrieve User")
        else:
            raise UserExists("User Does Not Exist")
    except Exception as e:
        raise e


def add_change_password_token(email, token):
    con = _connection()
    try:
        with con.cursor() as cursor:
            cursor.execute(queries["add_change_password_token"], (token, email))
        con.commit()
    except Exception:
        raise FailedToAddChangePasswordToken("Failed To Add Change Password Token")
    finally:
        con.close()


def add_confirmation_token(email, token):
    con = _connection()
    try:
        with con.cursor() as cursor:
            cursor.execute(queries["add_confirmation_token"], (token, email))
        con.commit()
    except Exception:
        raise FailedToAddConfirmationToken("Failed To Add Confirmation Token")
    finally:
        con.close()


def change_password(token, new_password):
    con = _connection()
    try:
        with con.cursor() as cursor:
            cursor.execute(queries["change_password"], (new_password, token))
        con.commit()
    except Exception:
        raise FailedToChangePassword("Failed To Change Password")
    finally:
        con.close()


def delete_user_given_email(email):
    con = _connection()
    try:
        with con.cursor() as cursor:
            cursor.execute(queries["delete_user"], email)
        con.commit()
    except Exception:
        raise FailedToDeleteUser("Failed To Delete User")
    finally:
        con.close()


def add_file_submitted(email, filename):
    con = _connection()
    try:
        with con.cursor() as cursor:
            cursor.execute(queries["add_file_submitted"], (filename, email))
        con.commit()
    except Exception:
        raise FailedToAddFile("Failed To Add File")
    finally:
        con.close()


def remove_file_entry(email):
    con = _connection()
    try:
        with con.cursor() as cursor:
            cursor.execute(queries["delete_file_submitted"], email)
        con.commit()
    except Exception:
        raise FailedToRemoveFileEntry("Failed To Remove File")
    finally:
        con.close()
