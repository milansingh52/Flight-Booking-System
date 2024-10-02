from django.shortcuts import render, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout

from datetime import datetime
import math
from .models import *
from capstone.utils import render_to_pdf, createticket


#Fee and Surcharge variable
from .constant import FEE
from datetime import datetime
from flight.utils import createWeekDays, addPlaces, addDomesticFlights, addInternationalFlights

# model
# import joblib
# model = joblib.load('static/add_model_new.pkl', "rb")

import sklearn
import pickle
import pandas as pd

model = pickle.load(open("flight_rf3.pkl", "rb"))




try:
    if len(Week.objects.all()) == 0:
        createWeekDays()

    if len(Place.objects.all()) == 0:
        addPlaces()

    if len(Flight.objects.all()) == 0:
        print("Do you want to add flights in the Database? (y/n)")
        if input().lower() in ['y', 'yes']:
            addDomesticFlights()
            addInternationalFlights()
except:
    pass

# Create your views here.

def index(request):
    min_date = f"{datetime.now().date().year}-{datetime.now().date().month}-{datetime.now().date().day}"
    max_date = f"{datetime.now().date().year if (datetime.now().date().month+3)<=12 else datetime.now().date().year+1}-{(datetime.now().date().month + 3) if (datetime.now().date().month+3)<=12 else (datetime.now().date().month+3-12)}-{datetime.now().date().day}"
    if request.method == 'POST':
        # extract 
        airline = request.POST.get('airline')
        stops = request.POST.get('stops')
        dept_time = request.POST.get('dept_time')
        arr_time = request.POST.get('arr_time')

        origin = request.POST.get('Origin')
        destination = request.POST.get('Destination')
        depart_date = request.POST.get('DepartDate')
        seat = request.POST.get('SeatClass')
        trip_type = request.POST.get('TripType')

        print(trip_type, seat, airline, stops, dept_time, arr_time, origin, destination, depart_date)
        print('hello')
        if(trip_type == '1'):
            return render(request, 'flight/index.html', {
            'origin': origin,
            'destination': destination,
            'depart_date': depart_date,
            'seat': seat.lower(),
            'trip_type': trip_type
        })
        elif(trip_type == '2'):
            return_date = request.POST.get('ReturnDate')
            return render(request, 'flight/index.html', {
            'min_date': min_date,
            'max_date': max_date,
            'origin': origin,
            'destination': destination,
            'depart_date': depart_date,
            'seat': seat.lower(),
            'trip_type': trip_type,
            'return_date': return_date
        })
    else:
        return render(request, 'flight/index.html', {
            'min_date': min_date,
            'max_date': max_date
        })

def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
            
        else:
            return render(request, "flight/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse('index'))
        else:
            return render(request, "flight/login.html")

def register_view(request):
    if request.method == "POST":
        fname = request.POST['firstname']
        lname = request.POST['lastname']
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensuring password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "flight/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.first_name = fname
            user.last_name = lname
            user.save()
        except:
            return render(request, "flight/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "flight/register.html")

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))

def query(request, q):
    places = Place.objects.all()
    filters = []
    q = q.lower()
    for place in places:
        if (q in place.city.lower()) or (q in place.airport.lower()) or (q in place.code.lower()) or (q in place.country.lower()):
            filters.append(place)
    return JsonResponse([{'code':place.code, 'city':place.city, 'country': place.country} for place in filters], safe=False)

@csrf_exempt
def flight(request):
    o_place = request.GET.get('Origin')
    d_place = request.GET.get('Destination')
    trip_type = request.GET.get('TripType')
    departdate = request.GET.get('DepartDate')

    # Convert the string to a datetime object
    depart_date_obj = datetime.strptime(departdate, "%m/%d/%Y")

    # Format the datetime object to the desired string format
    depart_date = depart_date_obj.strftime("%Y-%m-%d")
    print("dtime=", depart_date)

    return_date = None

    # extra
    airline = request.GET.get('airline')
    stops = request.GET.get('stops')
    dept_time = request.GET.get('dept_time')
    arr_time = request.GET.get('arr_time')
    

    if trip_type == '2':
        returndate = request.GET.get('ReturnDate')
        return_date = datetime.strptime(returndate, "%Y-%m-%d")
        flightday2 = Week.objects.get(number=return_date.weekday()) ##
        origin2 = Place.objects.get(code=d_place.upper())   ##
        destination2 = Place.objects.get(code=o_place.upper())  ##

    seat = request.GET.get('SeatClass')
    # flightday = Week.objects.get(number=depart_date.weekday())
    flightday = Week.objects.get(number=depart_date_obj.weekday())
    # print(flightday)
    destination = Place.objects.get(code=d_place.upper())
    origin = Place.objects.get(code=o_place.upper())
    
    if seat == 'economy':
        flights = Flight.objects.filter(depart_day=flightday,origin=origin,destination=destination).exclude(economy_fare=0).order_by('economy_fare')
        try:
            max_price = flights.last().economy_fare
            min_price = flights.first().economy_fare
        except:
            max_price = 0
            min_price = 0

        if trip_type == '2':    ##
            flights2 = Flight.objects.filter(depart_day=flightday2,origin=origin2,destination=destination2).exclude(economy_fare=0).order_by('economy_fare')    ##
            try:
                max_price2 = flights2.last().economy_fare   ##
                min_price2 = flights2.first().economy_fare  ##
            except:
                max_price2 = 0  ##
                min_price2 = 0  ##
                
    elif seat == 'business':
        flights = Flight.objects.filter(depart_day=flightday,origin=origin,destination=destination).exclude(business_fare=0).order_by('business_fare')
        try:
            max_price = flights.last().business_fare
            min_price = flights.first().business_fare
        except:
            max_price = 0
            min_price = 0

        if trip_type == '2':    ##
            flights2 = Flight.objects.filter(depart_day=flightday2,origin=origin2,destination=destination2).exclude(business_fare=0).order_by('business_fare')    ##
            try:
                max_price2 = flights2.last().business_fare   ##
                min_price2 = flights2.first().business_fare  ##
            except:
                max_price2 = 0  ##
                min_price2 = 0  ##

    elif seat == 'first':
        flights = Flight.objects.filter(depart_day=flightday,origin=origin,destination=destination).exclude(first_fare=0).order_by('first_fare')
        try:
            max_price = flights.last().first_fare
            min_price = flights.first().first_fare
        except:
            max_price = 0
            min_price = 0
            
        if trip_type == '2':    ##
            flights2 = Flight.objects.filter(depart_day=flightday2,origin=origin2,destination=destination2).exclude(first_fare=0).order_by('first_fare')
            try:
                max_price2 = flights2.last().first_fare   ##
                min_price2 = flights2.first().first_fare  ##
            except:
                max_price2 = 0  ##
                min_price2 = 0  ##    ##
    
    print(trip_type, seat, airline, stops, dept_time, arr_time, o_place, d_place, departdate)

    #print(calendar.day_name[depart_date.weekday()])
    if trip_type == '2':
        return render(request, "flight/search.html", {
            'flights': flights,
            'origin': origin,
            'destination': destination,
            'flights2': flights2,   ##
            'origin2': origin2,    ##
            'destination2': destination2,    ##
            'seat': seat.capitalize(),
            'trip_type': trip_type,
            'depart_date': depart_date,
            'return_date': return_date,
            'max_price': math.ceil(max_price/100)*100,
            'min_price': math.floor(min_price/100)*100,
            'max_price2': math.ceil(max_price2/100)*100,    ##
            'min_price2': math.floor(min_price2/100)*100    ##
        })
    else:
        return render(request, "flight/search.html", {
            'flights': flights,
            'origin': origin,
            'destination': destination,
            'seat': seat.capitalize(),
            'trip_type': trip_type,
            'depart_date': depart_date,
            'return_date': return_date,
            'max_price': math.ceil(max_price/100)*100,
            'min_price': math.floor(min_price/100)*100
        })

def review(request):
    flight_1 = request.GET.get('flight1Id')
    date1 = request.GET.get('flight1Date')
    print(date1)
    seat = request.GET.get('seatClass')
    round_trip = False
    if request.GET.get('flight2Id'):
        round_trip = True

    if round_trip:
        flight_2 = request.GET.get('flight2Id')
        date2 = request.GET.get('flight2Date')

    if request.user.is_authenticated:
        flight1 = Flight.objects.get(id=flight_1)
        # flight1ddate = datetime(int(date1.split('-')[2]),int(date1.split('-')[1]),int(date1.split('-')[0]),flight1.depart_time.hour,flight1.depart_time.minute)
        # flight1adate = (flight1ddate + flight1.duration)
        
        year, month, day = map(int, date1.split('-'))
        flight1ddate = datetime(year, month, day, flight1.depart_time.hour, flight1.depart_time.minute)
        flight1adate = flight1ddate + flight1.duration
        flight2 = None
        flight2ddate = None
        flight2adate = None
        if round_trip:
            flight2 = Flight.objects.get(id=flight_2)
            flight2ddate = datetime(int(date2.split('-')[2]),int(date2.split('-')[1]),int(date2.split('-')[0]),flight2.depart_time.hour,flight2.depart_time.minute)
            flight2adate = (flight2ddate + flight2.duration)
        #print("//////////////////////////////////")
        #print(f"flight1ddate: {flight1adate-flight1ddate}")
        #print("//////////////////////////////////")
        if round_trip:
            return render(request, "flight/book.html", {
                'flight1': flight1,
                'flight2': flight2,
                "flight1ddate": flight1ddate,
                "flight1adate": flight1adate,
                "flight2ddate": flight2ddate,
                "flight2adate": flight2adate,
                "seat": seat,
                "fee": FEE
            })
        return render(request, "flight/book.html", {
            'flight1': flight1,
            "flight1ddate": flight1ddate,
            "flight1adate": flight1adate,
            "seat": seat,
            "fee": FEE
        })
    else:
        return HttpResponseRedirect(reverse("login"))

def book(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            flight_1 = request.POST.get('flight1')
            flight_1date = request.POST.get('flight1Date')
            flight_1class = request.POST.get('flight1Class')
            f2 = False
            if request.POST.get('flight2'):
                flight_2 = request.POST.get('flight2')
                flight_2date = request.POST.get('flight2Date')
                flight_2class = request.POST.get('flight2Class')
                f2 = True
            countrycode = request.POST['countryCode']
            mobile = request.POST['mobile']
            email = request.POST['email']
            flight1 = Flight.objects.get(id=flight_1)
            if f2:
                flight2 = Flight.objects.get(id=flight_2)
            passengerscount = request.POST['passengersCount']
            passengers=[]
            for i in range(1,int(passengerscount)+1):
                fname = request.POST[f'passenger{i}FName']
                lname = request.POST[f'passenger{i}LName']
                gender = request.POST[f'passenger{i}Gender']
                passengers.append(Passenger.objects.create(first_name=fname,last_name=lname,gender=gender.lower()))
            coupon = request.POST.get('coupon')
            
            try:
                ticket1 = createticket(request.user,passengers,passengerscount,flight1,flight_1date,flight_1class,coupon,countrycode,email,mobile)
                if f2:
                    ticket2 = createticket(request.user,passengers,passengerscount,flight2,flight_2date,flight_2class,coupon,countrycode,email,mobile)

                if(flight_1class == 'Economy'):
                    if f2:
                        fare = (flight1.economy_fare*int(passengerscount))+(flight2.economy_fare*int(passengerscount))
                    else:
                        fare = flight1.economy_fare*int(passengerscount)
                elif (flight_1class == 'Business'):
                    if f2:
                        fare = (flight1.business_fare*int(passengerscount))+(flight2.business_fare*int(passengerscount))
                    else:
                        fare = flight1.business_fare*int(passengerscount)
                elif (flight_1class == 'First'):
                    if f2:
                        fare = (flight1.first_fare*int(passengerscount))+(flight2.first_fare*int(passengerscount))
                    else:
                        fare = flight1.first_fare*int(passengerscount)
            except Exception as e:
                return HttpResponse(e)
            

            if f2:    ##
                return render(request, "flight/payment.html", { ##
                    'fare': fare+FEE,   ##
                    'ticket': ticket1.id,   ##
                    'ticket2': ticket2.id   ##
                })  ##
            return render(request, "flight/payment.html", {
                'fare': fare+FEE,
                'ticket': ticket1.id
            })
        else:
            return HttpResponseRedirect(reverse("login"))
    else:
        return HttpResponse("Method must be post.")

def payment(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            ticket_id = request.POST['ticket']
            t2 = False
            if request.POST.get('ticket2'):
                ticket2_id = request.POST['ticket2']
                t2 = True
            fare = request.POST.get('fare')
            card_number = request.POST['cardNumber']
            card_holder_name = request.POST['cardHolderName']
            exp_month = request.POST['expMonth']
            exp_year = request.POST['expYear']
            cvv = request.POST['cvv']

            try:
                ticket = Ticket.objects.get(id=ticket_id)
                ticket.status = 'CONFIRMED'
                ticket.booking_date = datetime.now()
                ticket.save()
                if t2:
                    ticket2 = Ticket.objects.get(id=ticket2_id)
                    ticket2.status = 'CONFIRMED'
                    ticket2.save()
                    return render(request, 'flight/payment_process.html', {
                        'ticket1': ticket,
                        'ticket2': ticket2
                    })
                return render(request, 'flight/payment_process.html', {
                    'ticket1': ticket,
                    'ticket2': ""
                })
            except Exception as e:
                return HttpResponse(e)
        else:
            return HttpResponse("Method must be post.")
    else:
        return HttpResponseRedirect(reverse('login'))


def ticket_data(request, ref):
    ticket = Ticket.objects.get(ref_no=ref)
    return JsonResponse({
        'ref': ticket.ref_no,
        'from': ticket.flight.origin.code,
        'to': ticket.flight.destination.code,
        'flight_date': ticket.flight_ddate,
        'status': ticket.status
    })

@csrf_exempt
def get_ticket(request):
    ref = request.GET.get("ref")
    ticket1 = Ticket.objects.get(ref_no=ref)
    data = {
        'ticket1':ticket1,
        'current_year': datetime.now().year
    }
    pdf = render_to_pdf('flight/ticket.html', data)
    return HttpResponse(pdf, content_type='application/pdf')


def bookings(request):
    if request.user.is_authenticated:
        tickets = Ticket.objects.filter(user=request.user).order_by('-booking_date')
        return render(request, 'flight/bookings.html', {
            'page': 'bookings',
            'tickets': tickets
        })
    else:
        return HttpResponseRedirect(reverse('login'))

@csrf_exempt
def cancel_ticket(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            ref = request.POST['ref']
            try:
                ticket = Ticket.objects.get(ref_no=ref)
                if ticket.user == request.user:
                    ticket.status = 'CANCELLED'
                    ticket.save()
                    return JsonResponse({'success': True})
                else:
                    return JsonResponse({
                        'success': False,
                        'error': "User unauthorised"
                    })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': e
                })
        else:
            return HttpResponse("User unauthorised")
    else:
        return HttpResponse("Method must be POST.")

def resume_booking(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            ref = request.POST['ref']
            ticket = Ticket.objects.get(ref_no=ref)
            if ticket.user == request.user:
                return render(request, "flight/payment.html", {
                    'fare': ticket.total_fare,
                    'ticket': ticket.id
                })
            else:
                return HttpResponse("User unauthorised")
        else:
            return HttpResponseRedirect(reverse("login"))
    else:
        return HttpResponse("Method must be post.")

def contact_us(request):
    return render(request, 'flight/contact_us.html')

def privacy_policy(request):
    return render(request, 'flight/privacy-policy.html')

def terms_and_conditions(request):
    return render(request, 'flight/terms.html')

def about_us(request):
    return render(request, 'flight/about.html')

def test(request):
    return render(request, 'flight/test.html')

def add(request):
    # if request.method == "POST":
    #     # Date_of_Journey
    #     date_dep = request.POST.get("Dep_Time")
    #     Journey_day = int(pd.to_datetime(date_dep, format="%Y-%m-%dT%H:%M").day)
    #     Journey_month = int(pd.to_datetime(date_dep, format ="%Y-%m-%dT%H:%M").month)
    #     # print("Journey Date : ",Journey_day, Journey_month)

    #     # Departure
    #     Dep_hour = int(pd.to_datetime(date_dep, format ="%Y-%m-%dT%H:%M").hour)
    #     Dep_min = int(pd.to_datetime(date_dep, format ="%Y-%m-%dT%H:%M").minute)
    #     # print("Departure : ",Dep_hour, Dep_min)

    #     # Arrival
    #     date_arr = request.POST.get("Arrival_Time")
    #     Arrival_hour = int(pd.to_datetime(date_arr, format ="%Y-%m-%dT%H:%M").hour)
    #     Arrival_min = int(pd.to_datetime(date_arr, format ="%Y-%m-%dT%H:%M").minute)
    #     # print("Arrival : ", Arrival_hour, Arrival_min)

    #     # Duration
    #     dur_hour = abs(Arrival_hour - Dep_hour)
    #     dur_min = abs(Arrival_min - Dep_min)
    #     # print("Duration : ", dur_hour, dur_min)

    #     # Total Stops
    #     Total_stops = int(request.POST.get("stops"))
    #     # print(Total_stops)

    #     # Airline
    #     # AIR ASIA = 0 (not in column)
    #     airline=request.POST.get("airline")
    #     if(airline=='Jet Airways'):
    #         Jet_Airways = 1
    #         IndiGo = 0
    #         Air_India = 0
    #         Multiple_carriers = 0
    #         SpiceJet = 0
    #         Vistara = 0
    #         GoAir = 0
    #         Multiple_carriers_Premium_economy = 0
    #         Jet_Airways_Business = 0
    #         Vistara_Premium_economy = 0
    #         Trujet = 0 

    #     elif (airline=='IndiGo'):
    #         Jet_Airways = 0
    #         IndiGo = 1
    #         Air_India = 0
    #         Multiple_carriers = 0
    #         SpiceJet = 0
    #         Vistara = 0
    #         GoAir = 0
    #         Multiple_carriers_Premium_economy = 0
    #         Jet_Airways_Business = 0
    #         Vistara_Premium_economy = 0
    #         Trujet = 0 

    #     elif (airline=='Air India'):
    #         Jet_Airways = 0
    #         IndiGo = 0
    #         Air_India = 1
    #         Multiple_carriers = 0
    #         SpiceJet = 0
    #         Vistara = 0
    #         GoAir = 0
    #         Multiple_carriers_Premium_economy = 0
    #         Jet_Airways_Business = 0
    #         Vistara_Premium_economy = 0
    #         Trujet = 0 
            
    #     elif (airline=='Multiple carriers'):
    #         Jet_Airways = 0
    #         IndiGo = 0
    #         Air_India = 0
    #         Multiple_carriers = 1
    #         SpiceJet = 0
    #         Vistara = 0
    #         GoAir = 0
    #         Multiple_carriers_Premium_economy = 0
    #         Jet_Airways_Business = 0
    #         Vistara_Premium_economy = 0
    #         Trujet = 0 
            
    #     elif (airline=='SpiceJet'):
    #         Jet_Airways = 0
    #         IndiGo = 0
    #         Air_India = 0
    #         Multiple_carriers = 0
    #         SpiceJet = 1
    #         Vistara = 0
    #         GoAir = 0
    #         Multiple_carriers_Premium_economy = 0
    #         Jet_Airways_Business = 0
    #         Vistara_Premium_economy = 0
    #         Trujet = 0 
            
    #     elif (airline=='Vistara'):
    #         Jet_Airways = 0
    #         IndiGo = 0
    #         Air_India = 0
    #         Multiple_carriers = 0
    #         SpiceJet = 0
    #         Vistara = 1
    #         GoAir = 0
    #         Multiple_carriers_Premium_economy = 0
    #         Jet_Airways_Business = 0
    #         Vistara_Premium_economy = 0
    #         Trujet = 0

    #     elif (airline=='GoAir'):
    #         Jet_Airways = 0
    #         IndiGo = 0
    #         Air_India = 0
    #         Multiple_carriers = 0
    #         SpiceJet = 0
    #         Vistara = 0
    #         GoAir = 1
    #         Multiple_carriers_Premium_economy = 0
    #         Jet_Airways_Business = 0
    #         Vistara_Premium_economy = 0
    #         Trujet = 0

    #     elif (airline=='Multiple carriers Premium economy'):
    #         Jet_Airways = 0
    #         IndiGo = 0
    #         Air_India = 0
    #         Multiple_carriers = 0
    #         SpiceJet = 0
    #         Vistara = 0
    #         GoAir = 0
    #         Multiple_carriers_Premium_economy = 1
    #         Jet_Airways_Business = 0
    #         Vistara_Premium_economy = 0
    #         Trujet = 0

    #     elif (airline=='Jet Airways Business'):
    #         Jet_Airways = 0
    #         IndiGo = 0
    #         Air_India = 0
    #         Multiple_carriers = 0
    #         SpiceJet = 0
    #         Vistara = 0
    #         GoAir = 0
    #         Multiple_carriers_Premium_economy = 0
    #         Jet_Airways_Business = 1
    #         Vistara_Premium_economy = 0
    #         Trujet = 0

    #     elif (airline=='Vistara Premium economy'):
    #         Jet_Airways = 0
    #         IndiGo = 0
    #         Air_India = 0
    #         Multiple_carriers = 0
    #         SpiceJet = 0
    #         Vistara = 0
    #         GoAir = 0
    #         Multiple_carriers_Premium_economy = 0
    #         Jet_Airways_Business = 0
    #         Vistara_Premium_economy = 1
    #         Trujet = 0
            
    #     elif (airline=='Trujet'):
    #         Jet_Airways = 0
    #         IndiGo = 0
    #         Air_India = 0
    #         Multiple_carriers = 0
    #         SpiceJet = 0
    #         Vistara = 0
    #         GoAir = 0
    #         Multiple_carriers_Premium_economy = 0
    #         Jet_Airways_Business = 0
    #         Vistara_Premium_economy = 0
    #         Trujet = 1

    #     else:
    #         Jet_Airways = 0
    #         IndiGo = 0
    #         Air_India = 0
    #         Multiple_carriers = 0
    #         SpiceJet = 0
    #         Vistara = 0
    #         GoAir = 0
    #         Multiple_carriers_Premium_economy = 0
    #         Jet_Airways_Business = 0
    #         Vistara_Premium_economy = 0
    #         Trujet = 0

    #     # print(Jet_Airways,
    #     #     IndiGo,
    #     #     Air_India,
    #     #     Multiple_carriers,
    #     #     SpiceJet,
    #     #     Vistara,
    #     #     GoAir,
    #     #     Multiple_carriers_Premium_economy,
    #     #     Jet_Airways_Business,
    #     #     Vistara_Premium_economy,
    #     #     Trujet)

    #     # Source
    #     # Banglore = 0 (not in column)
    #     Source = request.POST.get("Source")
    #     if (Source == 'Delhi'):
    #         s_Delhi = 1
    #         s_Kolkata = 0
    #         s_Mumbai = 0
    #         s_Chennai = 0

    #     elif (Source == 'Kolkata'):
    #         s_Delhi = 0
    #         s_Kolkata = 1
    #         s_Mumbai = 0
    #         s_Chennai = 0

    #     elif (Source == 'Mumbai'):
    #         s_Delhi = 0
    #         s_Kolkata = 0
    #         s_Mumbai = 1
    #         s_Chennai = 0

    #     elif (Source == 'Chennai'):
    #         s_Delhi = 0
    #         s_Kolkata = 0
    #         s_Mumbai = 0
    #         s_Chennai = 1

    #     else:
    #         s_Delhi = 0
    #         s_Kolkata = 0
    #         s_Mumbai = 0
    #         s_Chennai = 0

    #     # print(s_Delhi,
    #     #     s_Kolkata,
    #     #     s_Mumbai,
    #     #     s_Chennai)

    #     # Destination
    #     # Banglore = 0 (not in column)
    #     Source = request.POST.get("Destination")
    #     if (Source == 'Cochin'):
    #         d_Cochin = 1
    #         d_Delhi = 0
    #         d_New_Delhi = 0
    #         d_Hyderabad = 0
    #         d_Kolkata = 0
        
    #     elif (Source == 'Delhi'):
    #         d_Cochin = 0
    #         d_Delhi = 1
    #         d_New_Delhi = 0
    #         d_Hyderabad = 0
    #         d_Kolkata = 0

    #     elif (Source == 'New_Delhi'):
    #         d_Cochin = 0
    #         d_Delhi = 0
    #         d_New_Delhi = 1
    #         d_Hyderabad = 0
    #         d_Kolkata = 0

    #     elif (Source == 'Hyderabad'):
    #         d_Cochin = 0
    #         d_Delhi = 0
    #         d_New_Delhi = 0
    #         d_Hyderabad = 1
    #         d_Kolkata = 0

    #     elif (Source == 'Kolkata'):
    #         d_Cochin = 0
    #         d_Delhi = 0
    #         d_New_Delhi = 0
    #         d_Hyderabad = 0
    #         d_Kolkata = 1

    #     else:
    #         d_Cochin = 0
    #         d_Delhi = 0
    #         d_New_Delhi = 0
    #         d_Hyderabad = 0
    #         d_Kolkata = 0

    #     # print(
    #     #     d_Cochin,
    #     #     d_Delhi,
    #     #     d_New_Delhi,
    #     #     d_Hyderabad,
    #     #     d_Kolkata
    #     # )
        

    # #     ['Total_Stops', 'Journey_day', 'Journey_month', 'Dep_hour',
    # #    'Dep_min', 'Arrival_hour', 'Arrival_min', 'Duration_hours',
    # #    'Duration_mins', 'Airline_Air India', 'Airline_GoAir', 'Airline_IndiGo',
    # #    'Airline_Jet Airways', 'Airline_Jet Airways Business',
    # #    'Airline_Multiple carriers',
    # #    'Airline_Multiple carriers Premium economy', 'Airline_SpiceJet',
    # #    'Airline_Trujet', 'Airline_Vistara', 'Airline_Vistara Premium economy',
    # #    'Source_Chennai', 'Source_Delhi', 'Source_Kolkata', 'Source_Mumbai',
    # #    'Destination_Cochin', 'Destination_Delhi', 'Destination_Hyderabad',
    # #    'Destination_Kolkata', 'Destination_New Delhi']
        
    #     prediction=model.predict([[
    #         Total_stops,
    #         Journey_day,
    #         Journey_month,
    #         Dep_hour,
    #         Dep_min,
    #         Arrival_hour,
    #         Arrival_min,
    #         dur_hour,
    #         dur_min,
    #         Air_India,
    #         GoAir,
    #         IndiGo,
    #         Jet_Airways,
    #         Jet_Airways_Business,
    #         Multiple_carriers,
    #         Multiple_carriers_Premium_economy,
    #         SpiceJet,
    #         Trujet,
    #         Vistara,
    #         Vistara_Premium_economy,
    #         s_Chennai,
    #         s_Delhi,
    #         s_Kolkata,
    #         s_Mumbai,
    #         d_Cochin,
    #         d_Delhi,
    #         d_Hyderabad,
    #         d_Kolkata,
    #         d_New_Delhi
    #     ]])

    #     output=round(prediction[0],2)

    #     return render(request, 'flight/add.html',{'output': output,
    #                                         'prediction_text': 'Your Flight price is Rs.'})
    
    return render(request, 'flight/add.html')


def format_k(value):
    if value >= 1000:
        return f"{round(value / 1000, 1)}k"
    else:
        return str(value)

def predict(request):
    

    # extra
    airline = request.GET.get('airline')
    if(airline=='Buddha_Air'):
        airline_Buddha_Air = 1
        airline_Saurya_Airlines = 0
        airline_Shree_Airlines = 0
        airline_Summit_Air = 0
        airline_Tara_Air = 0
        airline_Yeti_Airlines = 0
    
    elif (airline=='Saurya_Airlines'):
        airline_Buddha_Air = 0
        airline_Saurya_Airlines = 1
        airline_Shree_Airlines = 0
        airline_Summit_Air = 0
        airline_Tara_Air = 0
        airline_Yeti_Airlines = 0

    elif (airline=='Shree_Airlines'):
        airline_Buddha_Air = 0
        airline_Saurya_Airlines = 0
        airline_Shree_Airlines = 1
        airline_Summit_Air = 0
        airline_Tara_Air = 0
        airline_Yeti_Airlines = 0
    
    elif (airline=='Summit_Air'):
        airline_Buddha_Air = 0
        airline_Saurya_Airlines = 0
        airline_Shree_Airlines = 0
        airline_Summit_Air = 1
        airline_Tara_Air = 0
        airline_Yeti_Airlines = 0

    elif (airline=='Tara_Air'):
        airline_Buddha_Air = 0
        airline_Saurya_Airlines = 0
        airline_Shree_Airlines = 0
        airline_Summit_Air = 0
        airline_Tara_Air = 1
        airline_Yeti_Airlines = 0

    elif (airline=='Yeti_Airlines'):
        airline_Buddha_Air = 0
        airline_Saurya_Airlines = 0
        airline_Shree_Airlines = 0
        airline_Summit_Air = 0
        airline_Tara_Air = 0
        airline_Yeti_Airlines = 1
    else:
        airline_Buddha_Air = 0
        airline_Saurya_Airlines = 0
        airline_Shree_Airlines = 0
        airline_Summit_Air = 0
        airline_Tara_Air = 0
        airline_Yeti_Airlines = 0      

    stops = request.GET.get('stops')
    if(stops == "zero") :
        stops = 0
    elif(stops == "one"):
        stops = 1
    else:
        stops = 2

    air_class = request.GET.get('SeatClass')
    if(air_class == "economy"):
        air_class = 0
    else:
        air_class = 1

    dept_time = request.GET.get('dept_time')
    if(dept_time == "morning"):
        departure_Afternoon = 0
        departure_Early_Morning = 0
        departure_Evening = 0
        departure_Late_Night = 0
        departure_Morning = 1
        departure_Night = 0

    elif(dept_time == "early morning"):
        departure_Afternoon = 0
        departure_Early_Morning = 1
        departure_Evening = 0
        departure_Late_Night = 0
        departure_Morning = 0
        departure_Night = 0

    elif(dept_time == "afternoon"):
        departure_Afternoon = 1
        departure_Early_Morning = 0
        departure_Evening = 0
        departure_Late_Night = 0
        departure_Morning = 0
        departure_Night = 0

    elif(dept_time == "evening"):
        departure_Afternoon = 0
        departure_Early_Morning = 0
        departure_Evening = 1
        departure_Late_Night = 0
        departure_Morning = 0
        departure_Night = 0

    elif(dept_time == "night"):
        departure_Afternoon = 0
        departure_Early_Morning = 0
        departure_Evening = 0
        departure_Late_Night = 0
        departure_Morning = 0
        departure_Night = 1

    elif(dept_time == "late night"):
        departure_Afternoon = 0
        departure_Early_Morning = 0
        departure_Evening = 0
        departure_Late_Night = 1
        departure_Morning = 0
        departure_Night = 0
    
    else:
        departure_Afternoon = 0
        departure_Early_Morning = 0
        departure_Evening = 0
        departure_Late_Night = 0
        departure_Morning = 0
        departure_Night = 0

    arr_time = request.GET.get('arr_time')
    if(arr_time == "morning"):
        arrival_Afternoon = 0
        arrival_Early_Morning = 0
        arrival_Evening = 0
        arrival_Late_Night = 0
        arrival_Morning = 1
        arrival_Night = 0

    elif(arr_time == "early morning"):
        arrival_Afternoon = 0
        arrival_Early_Morning = 1
        arrival_Evening = 0
        arrival_Late_Night = 0
        arrival_Morning = 0
        arrival_Night = 0

    elif(arr_time == "afternoon"):
        arrival_Afternoon = 1
        arrival_Early_Morning = 0
        arrival_Evening = 0
        arrival_Late_Night = 0
        arrival_Morning = 0
        arrival_Night = 0

    elif(arr_time == "evening"):
        arrival_Afternoon = 0
        arrival_Early_Morning = 0
        arrival_Evening = 1
        arrival_Late_Night = 0
        arrival_Morning = 0
        arrival_Night = 0

    elif(arr_time == "night"):
        arrival_Afternoon = 0
        arrival_Early_Morning = 0
        arrival_Evening = 0
        arrival_Late_Night = 0
        arrival_Morning = 0
        arrival_Night = 1

    elif(arr_time == "late night"):
        arrival_Afternoon = 0
        arrival_Early_Morning = 0
        arrival_Evening = 0
        arrival_Late_Night = 1
        arrival_Morning = 0
        arrival_Night = 0
    
    else:
        arrival_Afternoon = 0
        arrival_Early_Morning = 0
        arrival_Evening = 0
        arrival_Late_Night = 0
        arrival_Morning = 0
        arrival_Night = 0

    o_place = request.GET.get('Origin')
    source = request.GET.get('Origin')

    if(o_place == "KTM"):
        o_place = "kathmandu"
    elif(o_place == "BWA"):
        o_place = "bhairahawa"
    elif(o_place == "PKR"):
        o_place = "pokhara"
    elif(o_place == "BRT"):
        o_place = "biratnagar"
    elif(o_place == "NPJ"):
        o_place = "nepalgunj"
    elif(o_place == "JNK"):
        o_place = "janakpur"

    if(o_place == "kathmandu"):
        source_Bhairahawa = 0
        source_Biratnagar = 0
        source_Janakpur = 0
        source_Kathmandu = 1
        source_Nepalgunj = 0
        source_Pokhara = 0

    elif(o_place == "bhairahawa"):
        source_Bhairahawa = 1
        source_Biratnagar = 0
        source_Janakpur = 0
        source_Kathmandu = 0
        source_Nepalgunj = 0
        source_Pokhara = 0

    elif(o_place == "biratnagar"):
        source_Bhairahawa = 0
        source_Biratnagar = 1
        source_Janakpur = 0
        source_Kathmandu = 0
        source_Nepalgunj = 0
        source_Pokhara = 0

    elif(o_place == "janakpur"):
        source_Bhairahawa = 0
        source_Biratnagar = 0
        source_Janakpur = 1
        source_Kathmandu = 0
        source_Nepalgunj = 0
        source_Pokhara = 0

    elif(o_place == "nepalgunj"):
        source_Bhairahawa = 0
        source_Biratnagar = 0
        source_Janakpur = 0
        source_Kathmandu = 0
        source_Nepalgunj = 1
        source_Pokhara = 0

    elif(o_place == "pokhara"):
        source_Bhairahawa = 0
        source_Biratnagar = 0
        source_Janakpur = 0
        source_Kathmandu = 0
        source_Nepalgunj = 0
        source_Pokhara = 1

    else:
        source_Bhairahawa = 0
        source_Biratnagar = 0
        source_Janakpur = 0
        source_Kathmandu = 0
        source_Nepalgunj = 0
        source_Pokhara = 0


    d_place = request.GET.get('Destination')
    destination = request.GET.get('Destination')
    

    if(d_place == "KTM"):
        d_place = "kathmandu"
    elif(d_place == "BWA"):
        d_place = "bhairahawa"
    elif(d_place == "PKR"):
        d_place = "pokhara"
    elif(d_place == "BRT"):
        d_place = "biratnagar"
    elif(d_place == "NPJ"):
        d_place = "nepalgunj"
    elif(d_place == "JNK"):
        d_place = "janakpur"
    elif(d_place == "JUM"):
        d_place = "jumla"
    elif(d_place == "LUM"):
        d_place = "lumbini"
    elif(d_place == "MAK"):
        d_place = "makanpur"
    elif(d_place == "TUL"):
        d_place = "tulsipur"

    if(d_place == "bhairahawa"):
        dest_Bhairahawa = 1
        dest_Biratnagar = 0
        dest_Jumla = 0
        dest_Kathmandu = 0
        dest_Lumbini = 0
        dest_Makanpur = 0
        dest_Nepalgunj = 0
        dest_Pokhara = 0
        dest_Tulsipur = 0

    elif(d_place == "biratnagar"):
        dest_Bhairahawa = 0
        dest_Biratnagar = 1
        dest_Jumla = 0
        dest_Kathmandu = 0
        dest_Lumbini = 0
        dest_Makanpur = 0
        dest_Nepalgunj = 0
        dest_Pokhara = 0
        dest_Tulsipur = 0

    elif(d_place == "jumla"):
        dest_Bhairahawa = 0
        dest_Biratnagar = 0
        dest_Jumla = 1
        dest_Kathmandu = 0
        dest_Lumbini = 0
        dest_Makanpur = 0
        dest_Nepalgunj = 0
        dest_Pokhara = 0
        dest_Tulsipur = 0

    elif(d_place == "kathmandu"):
        dest_Bhairahawa = 0
        dest_Biratnagar = 0
        dest_Jumla = 0
        dest_Kathmandu = 1
        dest_Lumbini = 0
        dest_Makanpur = 0
        dest_Nepalgunj = 0
        dest_Pokhara = 0
        dest_Tulsipur = 0

    elif(d_place == "lumbini"):
        dest_Bhairahawa = 0
        dest_Biratnagar = 0
        dest_Jumla = 0
        dest_Kathmandu = 0
        dest_Lumbini = 1
        dest_Makanpur = 0
        dest_Nepalgunj = 0
        dest_Pokhara = 0
        dest_Tulsipur = 0

    elif(d_place == "makanpur"):
        dest_Bhairahawa = 0
        dest_Biratnagar = 0
        dest_Jumla = 0
        dest_Kathmandu = 0
        dest_Lumbini = 0
        dest_Makanpur = 1
        dest_Nepalgunj = 0
        dest_Pokhara = 0
        dest_Tulsipur = 0

    elif(d_place == "nepalgunj"):
        dest_Bhairahawa = 0
        dest_Biratnagar = 0
        dest_Jumla = 0
        dest_Kathmandu = 0
        dest_Lumbini = 0
        dest_Makanpur = 0
        dest_Nepalgunj = 1
        dest_Pokhara = 0
        dest_Tulsipur = 0

    elif(d_place == "pokhara"):
        dest_Bhairahawa = 0
        dest_Biratnagar = 0
        dest_Jumla = 0
        dest_Kathmandu = 0
        dest_Lumbini = 0
        dest_Makanpur = 0
        dest_Nepalgunj = 0
        dest_Pokhara = 1
        dest_Tulsipur = 0

    elif(d_place == "tulsipur"):
        dest_Bhairahawa = 0
        dest_Biratnagar = 0
        dest_Jumla = 0
        dest_Kathmandu = 0
        dest_Lumbini = 0
        dest_Makanpur = 0
        dest_Nepalgunj = 0
        dest_Pokhara = 0
        dest_Tulsipur = 1

    else:
        dest_Bhairahawa = 0
        dest_Biratnagar = 0
        dest_Jumla = 0
        dest_Kathmandu = 0
        dest_Lumbini = 0
        dest_Makanpur = 0
        dest_Nepalgunj = 0
        dest_Pokhara = 0
        dest_Tulsipur = 0
    
    predictions = []
    for days_left in range(1, 16):
        prediction = model.predict([[
            stops,
            air_class,
            days_left,
            airline_Buddha_Air,
            airline_Saurya_Airlines, 
            airline_Shree_Airlines,
            airline_Summit_Air, 
            airline_Tara_Air, 
            airline_Yeti_Airlines,
            source_Bhairahawa, 
            source_Biratnagar, 
            source_Janakpur,
            source_Kathmandu, 
            source_Nepalgunj, 
            source_Pokhara,
            dest_Bhairahawa, 
            dest_Biratnagar, 
            dest_Jumla, 
            dest_Kathmandu,
            dest_Lumbini, 
            dest_Makanpur, 
            dest_Nepalgunj, 
            dest_Pokhara,
            dest_Tulsipur, 
            arrival_Afternoon, 
            arrival_Early_Morning,
            arrival_Evening, 
            arrival_Late_Night, 
            arrival_Morning,
            arrival_Night, 
            departure_Afternoon, 
            departure_Early_Morning,
            departure_Evening, 
            departure_Late_Night, 
            departure_Morning,
            departure_Night
        ]])
    
        output = round(prediction[0], 2)
        formatted_output = format_k(output)
        predictions.append(formatted_output)

    print(airline, stops, air_class, dept_time, arr_time, o_place, d_place)
    print('home1 click')
    # Render the predictions list to the template
    return render(request, 'flight/index.html', 
                    {
                        'predictions': predictions,
                        'airline': airline,
                        'stops': stops,
                        'seat': air_class,
                        'dept_time': dept_time,
                        'arr_time': arr_time,
                        'origin': source,
                        'destination': destination
                })
    print(o_place, d_place, airline, stops, dept_time, arr_time, seat)
    return render(request, 'flight/index.html')