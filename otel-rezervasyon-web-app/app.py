from flask import Flask, render_template, request, redirect, url_for, flash  #Flask: Web uygulamasını oluşturmak için. digerleri yönlendirme işlemleri için.
from pymongo import MongoClient   #MongoClient: MongoDB veritabanına bağlanmak için.
from bson import ObjectId         #ObjectId: MongoDB'deki belgelerin benzersiz kimliklerini yönetmek için.
from datetime import datetime     #datetime: Tarih ve saat hesaplamaları yapmak için.
import certifi 

app = Flask(__name__)
app.secret_key = "otelrezervasyon"

MONGO_URI = "mongodb+srv://admin:admin@cluster0.gba7n.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["hotel_reservation_db"]
customers_collection = db["customers"]
reservations_collection = db["reservations"]



@app.route("/")
def index():                                   # ana sayfa yönlendirmesi
    return render_template("index.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
                                                                    #müşteri kaydını yönlendirir. get post methodu ile mongodb ye veri alışverişi saglar.
        customer = {"name": name, "email": email, "phone": phone}
        result = customers_collection.insert_one(customer)

        flash("Müşteri başarıyla kaydedildi!", "success")
        return redirect(url_for("index"))
    return render_template("register.html")





@app.route("/reserve", methods=["GET", "POST"])
def reserve():
    if request.method == "POST":
        customer_email = request.form["email"]
        check_in = datetime.strptime(request.form["check_in"], "%Y-%m-%d")
        check_out = datetime.strptime(request.form["check_out"], "%Y-%m-%d")
        room_count = int(request.form["room_count"])
        capacity = int(request.form["capacity"])

        existing_reservations = list(
            reservations_collection.find(
                {
                    "$or": [
                        {"check_in": {"$lt": check_out}, "check_out": {"$gt": check_in}}
                    ]
                }
            )
        )                                                                                            # rezervaston işlemlerinin oldugu kısımdır.

        total_reserved_rooms = sum(res["room_count"] for res in existing_reservations)
        available_rooms = 10 - total_reserved_rooms

        if room_count <= available_rooms:
            customer = customers_collection.find_one({"email": customer_email})
            if customer:
                reservation = {
                    "customer_id": customer["_id"],
                    "check_in": check_in,
                    "check_out": check_out,
                    "room_count": room_count,
                    "capacity": capacity,
                }
                reservations_collection.insert_one(reservation)
                flash("Rezervasyon başarıyla yapıldı!", "success")
                return redirect(url_for("index"))
            else:
                flash("Müşteri bulunamadı. Önce kayıt olunuz.", "error")
        else:
            flash(f"Üzgünüz, şu anda sadece {available_rooms} oda müsait.", "error")

    return render_template("reserve.html")





@app.route("/reservations")
def list_reservations():
    reservations = list(
        reservations_collection.aggregate(
            [
                {
                    "$lookup": {
                        "from": "customers",
                        "localField": "customer_id",               #rezervasyonları listeme bölümü
                        "foreignField": "_id",
                        "as": "customer",
                    }
                },
                {"$unwind": "$customer"},
            ]
        )
    )
    return render_template("reservations.html", reservations=reservations)





@app.route("/cancel_reservation/<reservation_id>", methods=["POST"])
def cancel_reservation(reservation_id):
    reservations_collection.delete_one({"_id": ObjectId(reservation_id)})    #rezervasyon iptal kısmıdır.
    flash("Rezervasyon iptal edildi.", "success")
    return redirect(url_for("list_reservations"))



@app.route("/update_reservation/<reservation_id>", methods=["GET", "POST"])
def update_reservation(reservation_id):
    reservation = reservations_collection.find_one({"_id": ObjectId(reservation_id)})

    if request.method == "POST":
        try:
            new_check_in = datetime.strptime(request.form["check_in"], "%Y-%m-%d")
            new_check_out = datetime.strptime(request.form["check_out"], "%Y-%m-%d")
            new_room_count = int(request.form["room_count"])
            new_capacity = int(request.form["capacity"])

            existing_reservations = list(
                reservations_collection.find(
                    {
                        "_id": {"$ne": ObjectId(reservation_id)},
                        "$or": [
                            {
                                "check_in": {"$lt": new_check_out},
                                "check_out": {"$gt": new_check_in},
                            }
                        ],
                    }
                )
            )                                                                    #rezervasyon güncelleme kısmıdır. çakışmayı kontrol eder. yeterli oda varsa rezervasyonu günceller

            total_reserved_rooms = sum(
                res["room_count"] for res in existing_reservations
            )
            available_rooms = 10 - total_reserved_rooms
            if new_room_count <= available_rooms:
                reservations_collection.update_one(
                    {"_id": ObjectId(reservation_id)},
                    {
                        "$set": {
                            "check_in": new_check_in,
                            "check_out": new_check_out,
                            "room_count": new_room_count,
                            "capacity": new_capacity,
                        }
                    },
                )
                flash("Rezervasyon güncellendi!", "success")
                return redirect(url_for("list_reservations"))
            else:
                flash(f"Üzgünüz, şu anda sadece {available_rooms} oda müsait.", "error")
        except KeyError:
            flash("Lütfen tüm alanları doldurunuz.", "error")
        except ValueError:
            flash("Geçersiz tarih formatı.", "error")

    return render_template("update_reservation.html", reservation=reservation)




if __name__ == "__main__":              #Flask uygulamasını çalıştırır. Uygulama debug modunda çalışacak ve hata ayıklama işlemleri yapılabilir.    
    app.run(debug=True)
    