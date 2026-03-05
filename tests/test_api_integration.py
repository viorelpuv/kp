import pytest
import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="session")
def api_client():
    """Фикстура для создания HTTP-сессии"""
    session = requests.Session()
    yield session
    session.close()


@pytest.fixture(scope="session")
def check_server(api_client):
    """Фикстура для проверки доступности сервера"""
    try:
        response = api_client.get(f"{BASE_URL}/api/health", timeout=2)
        if response.status_code != 200:
            pytest.skip("Сервер не отвечает. Убедитесь, что он запущен на порту 8000")
    except:
        pytest.skip("Сервер не отвечает. Убедитесь, что он запущен на порту 8000")
    return True


class TestAPIIntegration:
    """Интеграционные тесты для API"""

    def test_1_get_trips_success(self, api_client, check_server):
        """Тест 1: Успешное получение списка рейсов"""
        response = api_client.get(f"{BASE_URL}/api/trips")
        assert response.status_code == 200

        data = response.json()
        assert "trips" in data
        assert "count" in data
        assert isinstance(data["trips"], list)

    def test_2_get_trips_with_filters(self, api_client, check_server):
        """Тест 2: Получение рейсов с фильтрацией"""
        params = {
            "departure": "Москва",
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        response = api_client.get(f"{BASE_URL}/api/trips", params=params)
        assert response.status_code == 200

        data = response.json()
        if data["trips"]:
            for trip in data["trips"]:
                assert trip["departure_station"] == "Москва"

    def test_3_get_trips_with_search(self, api_client, check_server):
        """Тест 3: Поиск рейсов"""
        params = {"search": "Сапсан"}
        response = api_client.get(f"{BASE_URL}/api/trips", params=params)
        assert response.status_code == 200

        data = response.json()
        if data["trips"]:
            for trip in data["trips"]:
                assert "Сапсан" in trip["train_name"]

    def test_4_get_trip_detail_success(self, api_client, check_server):
        """Тест 4: Успешное получение деталей рейса"""
        # Сначала получаем список рейсов
        trips_response = api_client.get(f"{BASE_URL}/api/trips")
        trips_data = trips_response.json()

        if trips_data["trips"]:
            trip_id = trips_data["trips"][0]["id"]

            response = api_client.get(f"{BASE_URL}/api/trips/{trip_id}")
            assert response.status_code == 200

            data = response.json()
            assert "id" in data
            assert "seats" in data
            assert "available_seats" in data

    def test_5_get_trip_detail_not_found(self, api_client, check_server):
        """Тест 5: Запрос несуществующего рейса"""
        response = api_client.get(f"{BASE_URL}/api/trips/99999")
        assert response.status_code == 404

    def test_6_trip_detail_has_seats(self, api_client, check_server):
        """Тест 6: Проверка наличия мест в деталях рейса"""
        trips_response = api_client.get(f"{BASE_URL}/api/trips")
        trips_data = trips_response.json()

        if trips_data["trips"]:
            trip_id = trips_data["trips"][0]["id"]

            response = api_client.get(f"{BASE_URL}/api/trips/{trip_id}")
            data = response.json()

            assert len(data["seats"]) > 0
            assert "seats_stats" in data

    def test_7_search_success(self, api_client, check_server):
        """Тест 7: Успешный поиск"""
        response = api_client.get(f"{BASE_URL}/api/search", params={"query": "Москва"})
        assert response.status_code == 200

        data = response.json()
        assert "results" in data
        assert "count" in data
        assert data["query"] == "Москва"

    def test_8_search_with_limit(self, api_client, check_server):
        """Тест 8: Поиск с ограничением результатов"""
        response = api_client.get(
            f"{BASE_URL}/api/search",
            params={"query": "а", "limit": 5}
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["results"]) <= 5

    def test_9_search_empty_query(self, api_client, check_server):
        """Тест 9: Поиск с пустым запросом"""
        response = api_client.get(f"{BASE_URL}/api/search", params={"query": ""})
        assert response.status_code == 200

        data = response.json()
        # API может возвращать все рейсы или пустой список
        # Проверяем только что это список
        assert isinstance(data["results"], list)

    def test_10_get_stats(self, api_client, check_server):
        """Тест 10: Получение статистики"""
        response = api_client.get(f"{BASE_URL}/api/stats")
        assert response.status_code == 200

        data = response.json()
        assert "total_tickets" in data
        assert "sold_tickets" in data
        assert "total_revenue" in data
        assert "total_trips" in data
        assert "free_seats" in data
