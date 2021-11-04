import json

from django.db.models import Avg
from django.shortcuts import render
from django.db import connections
from django.shortcuts import redirect
from django.http import Http404
from django.db.utils import IntegrityError
from django.views.generic import ListView

from app.utils import namedtuplefetchall, clamp
from app.forms import ImoForm
from app.models import Information, ShipType, VerifierCity

PAGE_SIZE = 20
COLUMNS = [
     'imo',
    'ship_name',
    'ship_type',
    'technical_efficiency_number',
    'issue_date',
    'expiry_date'
]

COLUMNSNEW = [
    'ship_type',
    'number_ships',
    'minimum_eedi',
    'average_eedi',
    'maximum_eedi'
]


def index(request):
    """Shows the main page"""
    context = {'nbar': 'home'}
    return render(request, 'index.html', context)


def db(request):
    """Shows very simple DB page"""
    with connections['default'].cursor() as cursor:
        cursor.execute('INSERT INTO app_greeting ("when") VALUES (NOW());')
        cursor.execute('SELECT "when" FROM app_greeting;')
        greetings = namedtuplefetchall(cursor)

    context = {'greetings': greetings, 'nbar': 'db'}
    return render(request, 'db.html', context)


def emissions(request, page=1):
    """Shows the emissions table page"""
    msg = None
    order_by = request.GET.get('order_by', '')
    order_by = order_by if order_by in COLUMNS else 'imo'

    with connections['default'].cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM co2emission_reduced')
        count = cursor.fetchone()[0]
        num_pages = (count - 1) // PAGE_SIZE + 1
        page = clamp(page, 1, num_pages)

        offset = (page - 1) * PAGE_SIZE
        cursor.execute(f'''
            SELECT {", ".join(COLUMNS)}
            FROM co2emission_reduced
            ORDER BY {order_by}
            OFFSET %s
            LIMIT %s
        ''', [offset, PAGE_SIZE])
        rows = namedtuplefetchall(cursor)

    imo_deleted = request.GET.get('deleted', False)
    if imo_deleted:
        msg = f'✔ IMO {imo_deleted} deleted'

    context = {
        'nbar': 'emissions',
        'page': page,
        'rows': rows,
        'num_pages': num_pages,
        'msg': msg,
        'order_by': order_by
    }
    return render(request, 'emissions.html', context)

def aggregation(request, page=1):
    """Shows the emissions aggregation table page"""
    msg = None
    order_by = request.GET.get('order_by', '')
    order_by = order_by if order_by in COLUMNSNEW else 'ship_type'

    with connections['default'].cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM aggregation')
        count = cursor.fetchone()[0]
        num_pages = (count - 1) // PAGE_SIZE + 1
        page = clamp(page, 1, num_pages)

        offset = (page - 1) * PAGE_SIZE
        cursor.execute(f'''
            SELECT {", ".join(COLUMNSNEW)}
            FROM aggregation
            ORDER BY {order_by}
            OFFSET %s
            LIMIT %s
        ''', [offset, PAGE_SIZE])
        rows = namedtuplefetchall(cursor)

    context = {
        'nbar': 'aggregation',
        'page': page,
        'rows': rows,
        'num_pages': num_pages,
        'order_by': order_by
    }
    return render(request, 'aggregation.html', context)


def visual(request, page=1):
    """Shows the visual page"""
    with connections['default'].cursor() as cursor:
        cursor.execute('SELECT ship_type, COUNT(DISTINCT(imo, ship_name)), MIN(technical_efficiency_number), AVG(technical_efficiency_number), MAX(technical_efficiency_number) FROM co2emission_reduced GROUP BY ship_type ORDER BY COUNT DESC')
        rows = namedtuplefetchall(cursor)
        
    labels = [row.ship_type for row in rows]
    count = [row.count for row in rows]
    min_avg = [[row.min, row.avg] for row in rows]
    avg_max = [[row.avg, row.max] for row in rows]
    
    context = {
        'labels': labels,
        'count': count,
        'min_avg': min_avg,
        'avg_max': avg_max
    }
    print(min_avg)
    print(avg_max)
    return render(request, 'visual.html', context)



def insert_update_values(form, post, action, imo):
    """
    Inserts or updates database based on values in form and action to take,
    and returns a tuple of whether action succeded and a message.
    """
    if not form.is_valid():
        return False, 'There were errors in your form'

    # Set values to None if left blank
    cols = COLUMNS[:]
    values = [post.get(col, None) for col in cols]
    values = [val if val != '' else None for val in values]

    if action == 'update':
        # Remove imo from updated fields
        cols, values = cols[1:], values[1:]
        with connections['default'].cursor() as cursor:
            cursor.execute(f'''
                UPDATE co2emission_reduced
                SET {", ".join(f"{col} = %s" for col in cols)}
                WHERE imo = %s;
            ''', [*values, imo])
        return True, '✔ IMO updated successfully'

    # Else insert
    with connections['default'].cursor() as cursor:
        cursor.execute(f'''
            INSERT INTO co2emission_reduced ({", ".join(cols)})
            VALUES ({", ".join(["%s"] * len(cols))});
        ''', values)
    return True, '✔ IMO inserted successfully'


def emission_detail(request, imo=None):
    """Shows the form where the user can insert or update an IMO"""
    success, form, msg, initial_values = False, None, None, {}
    is_update = imo is not None

    if is_update and request.GET.get('inserted', False):
        success, msg = True, f'✔ IMO {imo} inserted'

    if request.method == 'POST':
        # Since we set imo=disabled for updating, the value is not in the POST
        # data so we need to set it manually. Otherwise if we are doing an
        # insert, it will be None but filled out in the form
        if imo:
            request.POST._mutable = True
            request.POST['imo'] = imo
        else:
            imo = request.POST['imo']

        form = ImoForm(request.POST)
        action = request.POST.get('action', None)

        if action == 'delete':
            with connections['default'].cursor() as cursor:
                cursor.execute('DELETE FROM co2emission_reduced WHERE imo = %s;', [imo])
            return redirect(f'/emissions?deleted={imo}')
        try:
            success, msg = insert_update_values(form, request.POST, action, imo)
            if success and action == 'insert':
                return redirect(f'/emissions/imo/{imo}?inserted=true')
        except IntegrityError:
            success, msg = False, 'IMO already exists'
        except Exception as e:
            success, msg = False, f'Some unhandled error occured: {e}'
    elif imo:  # GET request and imo is set
        with connections['default'].cursor() as cursor:
            cursor.execute('SELECT * FROM co2emission_reduced WHERE imo = %s', [imo])
            try:
                initial_values = namedtuplefetchall(cursor)[0]._asdict()
            except IndexError:
                raise Http404(f'IMO {imo} not found')

    # Set dates (if present) to iso format, necessary for form
    # We don't use this in class, but you will need it for your project
    for field in ['doc_issue_date', 'doc_expiry_date']:
        if initial_values.get(field, None) is not None:
            initial_values[field] = initial_values[field].isoformat()

    # Initialize form if not done already
    form = form or ImoForm(initial=initial_values)
    if is_update:
        form['imo'].disabled = True

    context = {
        'nbar': 'emissions',
        'is_update': is_update,
        'imo': imo,
        'form': form,
        'msg': msg,
        'success': success
    }
    return render(request, 'emission_detail.html', context)


class ShipListView(ListView):
    template_name = 'ship.html'
    model = Information

    def get_queryset(self):
        ship_type = self.request.GET.getlist('ship_type')
        date = self.request.GET.get('date')
        selected_verifier_cities = self.request.GET.getlist('selected_verifier_cities')
        queryset = super(ShipListView, self).get_queryset()
        if all(ship_type):

            queryset = queryset.filter(ship_type__name__in=ship_type)
        if date:
            queryset = queryset.filter(date__date=date)
        if selected_verifier_cities:
            queryset = queryset.filter(verifier_city__name__in=selected_verifier_cities)
        return queryset

    def get_context_data(self, *, object_list=None, **kwargs):
        ship_types = ShipType.objects.all()
        queryset = self.get_queryset()
        d = []
        for ship_type in ship_types:
            eedi_avg = queryset.filter(ship_type=ship_type).aggregate(Avg('eedi'))
            d.append({
                'name': ship_type.name,
                'value': eedi_avg['eedi__avg']
            })
        context = super(ShipListView, self).get_context_data()
        context['d'] = json.dumps(d)
        context['ship_types'] = ship_types
        context['select_ship_types'] = self.request.GET.getlist('ship_type')
        context['verifier_cities'] = VerifierCity.objects.all()
        context['selected_verifier_cities'] = self.request.GET.getlist('selected_verifier_cities')
        return context
