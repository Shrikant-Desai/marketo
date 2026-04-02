# tests/factories.py
# factory_boy factories for generating test data.
# Requires: pip install factory-boy
import factory
from factory import Faker
from auth.security import hash_password


class UserFactory(factory.DictFactory):
    """Generates dicts suitable for UserRepository.create()."""
    email = Faker("email")
    username = Faker("user_name")
    password = factory.LazyFunction(lambda: hash_password("TestPass123!"))
    role = "user"
    is_active = True


class ProductFactory(factory.DictFactory):
    """Generates dicts suitable for ProductRepository.create()."""
    name = Faker("catch_phrase")
    price = factory.Faker("pyfloat", min_value=1.0, max_value=999.0, right_digits=2)
    sku = factory.Sequence(lambda n: f"MK-{n:04d}")
    category = factory.Iterator(["electronics", "clothing", "food", "books", "home"])
    description = Faker("text", max_nb_chars=200)
    stock = factory.Faker("random_int", min=0, max=100)
    is_active = True
    seller_id = 1  # override in tests


class OrderItemFactory(factory.DictFactory):
    product_id = 1  # override in tests
    quantity = factory.Faker("random_int", min=1, max=5)
    unit_price = factory.Faker("pyfloat", min_value=1.0, max_value=500.0, right_digits=2)
