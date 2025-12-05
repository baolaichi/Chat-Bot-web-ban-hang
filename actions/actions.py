from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import requests
from openai import OpenAI
import httpx  # <-- 1. THÊM IMPORT NÀY

# API SPRING BOOT
SPRING_BOOT_API_URL = "http://localhost:8080/api/internal-rasa"

# CẤU HÌNH DEEPSEEK
DEEPSEEK_API_KEY = "sk-7c0d45bebea34227ac1e0a80f6e756df" # Key bạn vừa lấy
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# Client xử lý kết nối
http_client = httpx.Client(timeout=60.0)


class ActionGetPrice(Action):
    def name(self) -> Text:
        return "action_get_price"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        product_name = next(tracker.get_latest_entity_values("product_name"), None)
        if not product_name:
            dispatcher.utter_message(response="utter_please_provide_product")
            return []
        try:
            response = requests.get(f"{SPRING_BOOT_API_URL}/product-price", params={"name": product_name})
            if response.status_code == 200:
                data = response.json()
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
        return "action_get_order_status"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        order_id = next(tracker.get_latest_entity_values("order_id"), None)
        if not order_id:
            dispatcher.utter_message(response="utter_please_provide_order")
            return []
        try:
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


# ===== ACTION GỌI DEEPSEEK (ĐÃ SỬA LỖI PROXIES) =====
class ActionChatWithLLM(Action):
    def name(self) -> Text:
        return "action_chat_with_llm"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_message = tracker.latest_message.get('text')
        if not user_message:
            return []

        dispatcher.utter_message(response="utter_wait_for_llm")

        try:
            # Khởi tạo Client trỏ về DeepSeek
            client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                http_client=http_client
            )

            response = client.chat.completions.create(
                model="deepseek-chat", # Model chuẩn của họ
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý ảo của LaptopShop..."},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=300,
                temperature=0.7
            )

            bot_reply = response.choices[0].message.content
            dispatcher.utter_message(text=bot_reply)

        except Exception as e:
            print(f"Lỗi DeepSeek: {e}")
            dispatcher.utter_message(text="Xin lỗi, AI đang bận. Bạn thử lại sau nhé.")

        return []


class ActionSearchProduct(Action):
    def name(self) -> Text:
        return "action_search_product"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        category = next(tracker.get_latest_entity_values("category"), None)
        brand = next(tracker.get_latest_entity_values("brand"), None)
        target = next(tracker.get_latest_entity_values("target"), None)
        params = {}
        if category: params['category'] = category
        if brand: params['brand'] = brand
        if target: params['target'] = target

        if not params:
            dispatcher.utter_message(text="Bạn vui lòng cho tôi biết thêm chi tiết (ví dụ: laptop, dell, gaming...)")
            return []

        try:
            response = requests.get(f"{SPRING_BOOT_API_URL}/search", params=params)
            if response.status_code == 200:
                products = response.json()
                if not products:
                    dispatcher.utter_message(response="utter_no_results")
                    return []
                results_text = []
                for p in products[:3]:
                    price_formatted = "{:,.0f}".format(p.get('price')).replace(",", ".")
                    results_text.append(f"- {p.get('name')} (Giá: {price_formatted} VNĐ)")
                formatted_results = "\n".join(results_text)
                if len(products) > 3:
                    formatted_results += f"\n... và {len(products) - 3} sản phẩm khác."
                dispatcher.utter_message(response="utter_search_results", search_results=formatted_results)
            else:
                dispatcher.utter_message(response="utter_no_results")
        except Exception as e:
            print(e)
            dispatcher.utter_message(response="utter_system_error")
        return []