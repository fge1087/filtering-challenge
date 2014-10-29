from django.db import models, connection
from django.db.models import Count, Q


class Order(models.Model):
    FCM = 'FCM'
    PRI = 'PRI'
    SHIPPING_CHOICES = (
        ('FCM', 'First Class Mail'),
        ('PRI', 'Priority Mail'),
    )
    shipping_method = models.CharField(max_length=100, choices=SHIPPING_CHOICES)
    date_completed = models.DateTimeField()
    
    @classmethod
    def split_by_shipping_method(cls):
        """ Return two lists of primary keys: one for orders done by First Class Mail, and one for
        orders done by Priority Mail."""
        fcm = list(cls.objects.filter(shipping_method='FCM').values_list('pk', flat=True))
        pri = list(cls.objects.filter(shipping_method='PRI').values_list('pk', flat=True))
        return fcm, pri
        
    @classmethod
    def split_by_single_and_multiple(cls):
        """ Return two lists of primary keys: one for orders that have only one item, and one for
        orders that have multiple items."""
        singles = list(cls.objects.annotate(Count('items')).filter(items__count=1).values_list('pk', flat=True))
        multiples = list(cls.objects.annotate(Count('items')).filter(items__count__gte=2).values_list('pk', flat=True))
        return singles, multiples
    
    @classmethod
    def single_orders_are_sorted(cls):
        """ Return list of orders with only one item, sorted by the priority denoted in the priority attribute of the OrderItem
        class (XS -> XXL)."""
        cursor = connection.cursor()
        cursor.execute("""SELECT innerQuery.id, orders_orderitem.product from (SELECT orders_order.id FROM orders_order LEFT OUTER JOIN orders_orderitem ON ( orders_order.id = orders_orderitem.order_id ) 
        GROUP BY orders_order.id, orders_order.shipping_method, orders_order.date_completed
        HAVING COUNT(orders_orderitem.id) = 1) innerQuery LEFT OUTER JOIN orders_orderitem ON (innerQuery.id = orders_orderitem.order_id)""")
        
        single_orders = cursor.fetchall()
        single_sorted_orders = [pk for (pk, product) in sorted(single_orders, key=lambda tup: OrderItem.priority[tup[1]])]
        return single_sorted_orders
    
    @classmethod
    def orders_split_by_xxl_and_not(cls):
        """ Return two lists of primary keys: one for multiple orders that include at least one 
        XXL shirt, and one for multiple orders that have no XXL shirts."""
        base_query = cls.objects.annotate(Count('items')).filter(items__count__gte=2)
        xxl = list(base_query.filter(items__product='XXL').values_list('pk', flat=True))
        not_xxl = list(base_query.filter(~Q(items__product = 'XXL')).values_list('pk', flat=True))
        return xxl, not_xxl
        


class OrderItem(models.Model):
    XS = 'XS'
    S = 'S'
    M = 'M'
    L = 'L'
    XL = 'XL'
    XXL = 'XXL'
    PRODUCT_CHOICES = (
        ('XS', 'Extra Small Tee'),
        ('S', 'Small Tee'),
        ('M', 'Medium Tee'),
        ('L', 'Large Tee'),
        ('XL', 'Extra Large Tee'),
        ('XXL', 'Double Extra Large Tee'),
    )
    priority = {'XS': 0, 'S': 1, 'M': 2, 'L': 3, 'XL': 4, 'XXL': 5}
    order = models.ForeignKey(Order, related_name='items')
    product = models.CharField(max_length=100, choices=PRODUCT_CHOICES)
    quantity = models.PositiveIntegerField(default=1)