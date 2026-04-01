from flask import Blueprint, request, session, redirect, url_for

auth = Blueprint("auth", __name__)

USERS = {
    "himanshu": "7323996467",
    "team1": "7323996467"
}

@auth.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in USERS and USERS[username] == password:
            session["user"] = username
            return redirect("/home")
        else:
            return "❌ Invalid credentials"

    return '''
    <h2>Login</h2>
    <form method="post">
        <input name="username"><br><br>
        <input name="password" type="password"><br><br>
        <button>Login</button>
    </form>
    '''

@auth.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")