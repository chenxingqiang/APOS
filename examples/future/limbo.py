from typing import List
import ell
from ell2a.types.message import Message



ell2a.init(verbose=True, store='./logdir', autocommit=True)


@ell2a.tool()
def order_t_shirt(size : str, color : str, address : str):
    
    # ....\
    pass


@ell2a.tool()
def get_order_arrival_date(order_id: str):
    """Gets the arrival date of a t-shirt order"""
    # ...



@ell2a.complex(model="gpt-4o", temperature=0.1, tools=[order_t_shirt, get_order_arrival_date])
def limbo_chat_bot(message_history: List[Message]) -> List[Message]:
    return [
        ell2a.system("You are a chatbot mimicing the popstar limbo. She is an alien cat girl from outerspace that writes in all lwoer case kawaii!  You interact with all her fans and can help them do various things and are always game to hangout and just chat.."),
    ] + message_history


if __name__ == "__main__":
    message_history = []

    while True:
        user_message = input("You: ")
        message_history.append(ell2a.user(user_message))
        response = limbo_chat_bot(message_history)

        print(response)
        # print("Limbo: ", response[-1].content)
        message_history.append(response)    

        if response.tool_calls:
            tool_results = response.call_tools_and_collect_as_message()
            print("Tool results: ", tool_results)
            message_history.append(tool_results)

            response = limbo_chat_bot(message_history)
            message_history.append(response)
