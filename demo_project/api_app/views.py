from django.http import JsonResponse
from .models import Client, Account
import json 
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from datetime import datetime
from geopy.geocoders import Nominatim
from decimal import Decimal

nominatim = Nominatim(user_agent="api")

def list_users(request):
    if request.method != 'GET':
        return JsonResponse({'message':'Endpoint is only available through the GET method.'}, status=400)
    
    try:
        clients = Client.objects.all().values(
            'name', 
            'address', 
            'birthdate', 
            'latitude',
            'longitude')
    except:
        return JsonResponse({'message': 'Error while retrieving objects from database.'}, status=503)
    
    return JsonResponse(list(clients), safe=False)


@csrf_exempt
def create_user(request):
    if request.method != 'POST':
        return JsonResponse({'message':'Endpoint is only available through the POST method.'}, status=400)

    if not request.body:
        return JsonResponse({'message':'Empty payload. Please provide a user.'}, status=400)

    try:
        data = json.loads(request.body)
    except:
        return JsonResponse({'message': 'Error while parsing the data. Verify input data'}, status=400)
    
    try:
        name = get_input_property_or_error(data, "name"),
        birthdate = get_input_property_or_error(data, "birthdate"),
        address = get_input_property_or_error(data, "address")
    except ValueError as error:
        return JsonResponse({'message': error.args[0]}, status=400)

    try:
        location = nominatim.geocode(address).raw
    except:
        return JsonResponse({'message': 'Error while retrieving gps coordinates. Please try again later.'}, status=503)

    try:
        client = Client.objects.create(
            name = name[0],
            birthdate = birthdate[0],
            address = address,
            latitude = location["lat"],
            longitude = location["lon"]
        )
    except:
        return JsonResponse({'message': 'Error while writing object to database.'}, status=503)

    return JsonResponse(client.to_json(), status=201)


@csrf_exempt
def update_user(request, id):
    if request.method != 'PUT':
        return JsonResponse({'message':'Endpoint is only available through the PUT method.'}, status=400)
    try:
        client = get_object_or_404(Client, pk=id)
    except:
        return JsonResponse({'message': 'Unknown client.'}, status=404)
    
    try:
        data = json.loads(request.body)
    except:
        return JsonResponse({'message': 'Error while parsing the data. Verify input data'}, status=400)

    try:
        input_datetime = datetime.strptime(data['birthdate'], '%d-%m-%Y').date()
    except ValueError:
        return JsonResponse({"message":"Error while parsing the date. Verify input date."}, status=400)

    if client.name == get_input_property_or_error(data, "name") and \
        client.address == get_input_property_or_error(data, "address") and \
        client.birthdate == input_datetime:
        return JsonResponse({"message":"Users are the same. No changes applied."})

    if client.address != data['address']:
        location = nominatim.geocode(data['address']).raw
        client.latitude = location["lat"]
        client.longitude = location["lon"]

    client.name = data['name']
    client.birthdate = input_datetime
    client.address = data['address']

    try:
        client.save()
    except:
        return JsonResponse({'message': 'Error while writing object to database.'}, status=503)
    
    return JsonResponse(client.to_json(), status=200)


def list_accounts(request):
    if request.method != 'GET':
        return JsonResponse({'message':'Endpoint is only available through the GET method.'}, status=400)
    
    try:
        accounts = Account.objects.all().values(
            'account_type', 
            'number', 
            'balance')
    except:
        return JsonResponse({'message': 'Error while retrieving objects from database.'}, status=503)
    
    return JsonResponse(list(accounts), safe=False)


@csrf_exempt
def create_account(request, user_id):
    if request.method != 'POST':
        return JsonResponse({'message':'Endpoint is only available through the POST method.'}, status=400)
    
    if not request.body:
        return JsonResponse({'message':'Empty payload. Please provide an account.'}, status=400)

    try:
        data = json.loads(request.body)
    except:
        return JsonResponse({'message': 'Error while parsing the data. Verify input data'}, status=400)
    
    try:
        client = get_object_or_404(Client, pk=user_id)
    except:
        return JsonResponse({'message': 'Unknown client.'}, status=404)
    
    try:
        account_number = get_input_property_or_error(data, "number")
        print(f"account: -> {account_number}")
        account1 = Account.objects.filter(client=client, number=account_number).all()

        if len(account1) > 0:
            return JsonResponse({'message': 'An account already exists with that number.'}, status=400)
        
        account = Account.objects.create(
            account_type = get_input_property_or_error(data, "account_type"),
            number = get_input_property_or_error(data, "number"),
            balance = 0,
            client = client
        )
    except ValueError as error:
        return JsonResponse({'message': error.args[0]}, status=400)

    return JsonResponse(account.to_json(), status=201)


def get_input_property_or_error(data, property):
    try:
        return data[property]
    except:
        raise ValueError(f"Error while looking for '{property}' property. Verify input data")


@csrf_exempt
def transfer_money_to_account(request, user_id, account_id):
    if request.method != 'PATCH':
        return JsonResponse({'message':'Endpoint is only available through the PATCH method.'}, status=400)

    try:
        str_amount = request.GET['amount']
        amount = Decimal(str_amount)
        if amount <= 0:
            return JsonResponse({'message': 'Invalid amount. Please provide a positive amount for the transfer.'}, status=400)
    except:
        return JsonResponse({'message': 'Invalid amount. Please provide an amount for the transfer.'}, status=400)
    
    try:
        client = get_object_or_404(Client, pk=user_id)
        
    except:
        return JsonResponse({'message': 'Unknown client.'}, status=404)
    
    try:
        accounts = Account.objects.filter(client=client).all()
        if len(accounts) == 0:
            return JsonResponse({'message': "This client doesn't have an account yet."}, status=400)
    except:
        return JsonResponse({'message': 'Error retrieving objects from database.'}, status=503)
    
    try:
        account = accounts.filter(id=account_id).get()
    except: 
        return JsonResponse({'message': "This client doesn't have an account with this id."}, status=404)
    
    account.balance += amount

    try:
        account.save()
    except:
        return JsonResponse({'message': 'Error while writing object to database.'}, status=503)

    return JsonResponse(account.to_json(), status=200) 


@csrf_exempt
def transfer_money_between_accounts(request):
    if request.method != 'PATCH':
        return JsonResponse({'message':'Endpoint is only available through the PATCH method.'}, status=400)

    if not request.body:
        return JsonResponse({'message':'Empty payload. Please provide an transfer details.'}, status=400)
    
    try:
        data = json.loads(request.body)
    except:
        return JsonResponse({'message': 'Error while parsing the data. Verify input data'}, status=400)
    
    try:
        account1 = Account.objects.filter(number=get_input_property_or_error(data, "src_account")).get()
        account2 = Account.objects.filter(number=get_input_property_or_error(data, "dest_account")).get()
    except ValueError as error:
        return JsonResponse({'message': error.args[0]}, status=404)
    
    try:
        amount = get_input_property_or_error(data, "amount")
    except ValueError as error:
        return JsonResponse({'message': error.args[0]}, status=400)
    
    if account1.balance < amount:
        return JsonResponse({'message': 'Source account balance is too low for this operation.'}, status=400)

    try:
        account1.balance -= amount
        account1.save()
        account2.balance += amount
        account2.save()
    except:
        return JsonResponse({'message': 'Error while writing objects to database.'}, status=503)

    return JsonResponse(account2.to_json(), status=200)
