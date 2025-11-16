# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import requests  # Thư viện bạn đã cài (pip install requests)

# ĐỊA CHỈ API CỦA SPRING BOOT (BẠN SẼ TẠO Ở PHẦN 2)
SPRING_BOOT_API_URL = "http://localhost:8080/api/internal-rasa"


class ActionGetPrice(Action):
    def name(self) -> Text:
        return "action_get_price"  # Tên phải khớp 100% với domain.yml

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # 1. Lấy thực thể "product_name" mà NLU nhận diện được
        product_name = next(tracker.get_latest_entity_values("product_name"), None)

        # 2. Nếu không tìm thấy tên sản phẩm
        if not product_name:
            dispatcher.utter_message(response="utter_please_provide_product")  # Gọi câu trả lời đã định nghĩa
            return []

        # 3. Nếu tìm thấy -> Gọi API Spring Boot
        try:
            # Gọi API GET: http://localhost:8080/api/internal-rasa/product-price?name=iPhone 15
            response = requests.get(
                f"{SPRING_BOOT_API_URL}/product-price",
                params={"name": product_name}
            )

            # 4. Xử lý kết quả từ Spring Boot
            if response.status_code == 200:
                data = response.json()
                # Định dạng giá tiền (ví dụ: 30000000 -> "30.000.000")
                price_formatted = "{:,.0f}".format(data.get('price')).replace(",", ".")
                dispatcher.utter_message(text=f"Giá của {product_name} hiện là {price_formatted} VNĐ ạ.")
            else:
                dispatcher.utter_message(text=f"Xin lỗi, tôi không tìm thấy sản phẩm '{product_name}' trong hệ thống.")

        except requests.exceptions.ConnectionError as e:
            print(f"Lỗi kết nối Spring Boot: {e}")
            dispatcher.utter_message(response="utter_system_error")

        return []


class ActionGetOrderStatus(Action):
    def name(self) -> Text:
        return "action_get_order_status"  # Tên phải khớp 100% với domain.yml

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        order_id = next(tracker.get_latest_entity_values("order_id"), None)

        if not order_id:
            dispatcher.utter_message(response="utter_please_provide_order")
            return []

        try:
            # Gọi API GET: http://localhost:8080/api/internal-rasa/order-status/12345
            response = requests.get(f"{SPRING_BOOT_API_URL}/order-status/{order_id}")

            if response.status_code == 200:
                data = response.json()
                dispatcher.utter_message(text=f"Đơn hàng {order_id} của bạn đang ở trạng thái: {data.get('status')}.")
            else:
                dispatcher.utter_message(text=f"Xin lỗi, tôi không tìm thấy đơn hàng có mã '{order_id}'.")

        except requests.exceptions.ConnectionError as e:
            print(f"Lỗi kết nối Spring Boot: {e}")
            dispatcher.utter_message(response="utter_system_error")

        return []