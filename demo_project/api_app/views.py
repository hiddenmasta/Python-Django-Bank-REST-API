
from django.http import JsonResponse
from .models import Client, Account
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json
import time
from datetime import datetime
from geopy.geocoders import Nominatim
from decimal import Decimal

nominatim = Nominatim(user_agent="api")

@csrf_exempt
def users_collection(request):
    if request.method == 'GET':
        try:
            clients = Client.objects.all().values(
                'id', 'name', 'address', 'birthdate', 'latitude', 'longitude')
        except Exception:
            return JsonResponse({'message': 'Error while retrieving objects from database.'}, status=503)
        return JsonResponse(list(clients), safe=False)

    elif request.method == 'POST':
        if not request.body:
            return JsonResponse({'message':'Empty payload. Please provide a user.'}, status=400)
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'message': 'Error while parsing the data. Verify input data'}, status=400)
        try:
            input_datetime = datetime.strptime(data['birthdate'], '%d-%m-%Y').date()
        except ValueError:
            return JsonResponse({"message":"Error while parsing the date. Verify input date."}, status=400)
        try:
            name = get_input_property_or_error(data, "name")
            address = get_input_property_or_error(data, "address")
            location = get_location_by_address(address)
            latitude = location["lat"]
            longitude = location["lon"]
            client = Client.objects.create(
                name=name,
                birthdate=input_datetime,
                address=address,
                latitude=latitude,
                longitude=longitude
            )
        except ValueError as error:
            return JsonResponse({'message': error.args[0]}, status=400)
        except Exception as error:
            return JsonResponse({'message': f'Error while writing object to database with {error}.'}, status=503)
        return JsonResponse(client.to_json(), status=201)

    else:
        return JsonResponse({'message': 'Method not allowed.'}, status=405)

@csrf_exempt
def user_detail(request, id):
    if request.method == 'PUT':
        try:
            client = get_object_or_404(Client, pk=id)
        except Exception:
            return JsonResponse({'message': 'Error while updating the client.'}, status=404)
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'message': 'Error while parsing the data. Verify input data'}, status=400)
        try:
            input_datetime = datetime.strptime(data['birthdate'], '%d-%m-%Y').date()
        except ValueError:
            return JsonResponse({"message":"Error while parsing the date. Verify input date."}, status=400)
        try:
            client.name = get_input_property_or_error(data, "name")
            client.address = get_input_property_or_error(data, "address")
            client.birthdate = input_datetime
            location = get_location_by_address(client.address)
            client.latitude = location["lat"]
            client.longitude = location["lon"]
            client.save()
        except ValueError as error:
            return JsonResponse({'message': error.args[0]}, status=400)
        except Exception as error:
            return JsonResponse({'message': f'Unexpected error while writing object to database: {error}.'}, status=503)
        return JsonResponse(client.to_json(), status=201)
    else:
        return JsonResponse({'message': 'Method not allowed.'}, status=405)

@csrf_exempt
def accounts_collection(request):
    if request.method == 'GET':
        try:
            accounts = Account.objects.all().values('account_type', 'number', 'balance')
        except Exception:
            return JsonResponse({'message': 'Error while retrieving objects from database.'}, status=503)
        return JsonResponse(list(accounts), safe=False)

    elif request.method == 'POST':
        if not request.body:
            return JsonResponse({'message':'Empty payload. Please provide an account.'}, status=400)
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'message': 'Error while parsing the data. Verify input data'}, status=400)
        try:
            user_id = get_input_property_or_error(data, "user_id")
            client = get_object_or_404(Client, pk=user_id)
            account_number = get_input_property_or_error(data, "number")
            if Account.objects.filter(client=client, number=account_number).exists():
                return JsonResponse({'message': 'An account already exists with that number.'}, status=400)
            account = Account.objects.create(
                account_type = get_input_property_or_error(data, "account_type"),
                number = account_number,
                balance = 0,
                client = client
            )
        except ValueError as error:
            return JsonResponse({'message': error.args[0]}, status=400)
        except Exception as error:
            return JsonResponse({'message': 'Error while writing object to database.'}, status=503)
        return JsonResponse(account.to_json(), status=201)

    else:
        return JsonResponse({'message': 'Method not allowed.'}, status=405)


def get_input_property_or_error(data, property):
    try:
        return data[property]
    except:
        raise ValueError(f"Error while looking for '{property}' property. Verify input data")



@csrf_exempt
def transfer_money_to_account(request, id):
    if request.method != 'PATCH':
        return JsonResponse({'message':'Endpoint is only available through the PATCH method.'}, status=400)
    if not request.body:
        return JsonResponse({'message':'Empty payload. Please provide transfer details.'}, status=400)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'message': 'Error while parsing the data. Verify input data'}, status=400)
    try:
        amount = Decimal(get_input_property_or_error(data, "amount"))
        if amount <= 0:
            return JsonResponse({'message': 'Invalid amount. Please provide a positive amount for the transfer.'}, status=400)
        
        with transaction.atomic():
            account = Account.objects.select_for_update().get(pk=id)
            account.balance += amount
            account.save()
    except Account.DoesNotExist:
        return JsonResponse({'message': 'Account not found.'}, status=404)
    except ValueError as error:
        return JsonResponse({'message': error.args[0]}, status=400)
    except Exception as error:
        return JsonResponse({'message': 'Error while writing object to database.'}, status=503)
    return JsonResponse(account.to_json(), status=200)



@csrf_exempt
def transfer_money_between_accounts(request):
    if request.method != 'POST':
        return JsonResponse({'message':'Endpoint is only available through the POST method.'}, status=400)
    if not request.body:
        return JsonResponse({'message':'Empty payload. Please provide transfer details.'}, status=400)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'message': 'Error while parsing the data. Verify input data'}, status=400)
    try:
        src_account_number = get_input_property_or_error(data, "src_account")
        dest_account_number = get_input_property_or_error(data, "dest_account")
        amount = Decimal(get_input_property_or_error(data, "amount"))
        
        if amount <= 0:
            return JsonResponse({'message': 'Invalid amount. Amount must be positive.'}, status=400)
        
        with transaction.atomic():
            # Lock both accounts in consistent order (by number) to prevent deadlock
            accounts = Account.objects.filter(
                number__in=[src_account_number, dest_account_number]
            ).select_for_update().order_by('number')
            
            account_dict = {acc.number: acc for acc in accounts}
            
            if src_account_number not in account_dict:
                return JsonResponse({'message': 'Source account not found.'}, status=404)
            if dest_account_number not in account_dict:
                return JsonResponse({'message': 'Destination account not found.'}, status=404)
            
            src_account = account_dict[src_account_number]
            dest_account = account_dict[dest_account_number]
            
            if src_account.balance < amount:
                return JsonResponse({'message': 'Source account balance is too low for this operation.'}, status=400)
            
            src_account.balance -= amount
            dest_account.balance += amount
            src_account.save()
            dest_account.save()
            
    except ValueError as error:
        return JsonResponse({'message': error.args[0]}, status=400)
    except Exception as error:
        return JsonResponse({'message': 'Error while writing objects to database.'}, status=503)
    return JsonResponse(dest_account.to_json(), status=200)

def get_location_by_address(address):
    """This function returns a location as raw from an address
    will repeat until success"""
    time.sleep(1)
    try:
        return nominatim.geocode(address).raw
    except:
        return get_location_by_address(address)