from stabilizer import Stabilizer
from config import *
import json
import time
from datetime import datetime as dt
from estimate_head_pose import get_score

class Exercise():
    def __init__(self):
        self.users = None
        self.username = None
        self.user = None
        with open(USERS_JSON, "r") as file:
            self.users = json.load(file)

    def prompt_user(self):
        self.username = input("-----------------------------\nWelcome to Exerciser. \nPlease tell me who you are: ")
        while self.username not in self.users.keys():
            print("\nAre you a new user? [y/n]")
            answer = input()
            if answer == "n":
                print("\nUsername not recognized. Please type the name again: ")
                self.username = input()
            else:
                self.user = self.create_new_user()
                # New user! Create new user.
                break
        
        if not self.user:
            self.user = self.users[self.username]
        print(f"Greetings {self.username}. Your credit score is: {self.user['score']}")
        return self.user

    def create_new_user(self):
        user = dict()
        user["score"] = 0
        print("Let's see how flexible you are. \nMove your head forwards and backwards, sideways and tilt to both sides.\nPress ESC when finished.")
        dev0, dev1, dev2 = get_score(mode=1)
        # The user will probably exercise way more than on daily basis, that's why
        # we will cut down on angle by 20 percent.
        user["threshold0"] = dev0 * 0.8
        user["threshold1"] = dev1 * 0.8
        user["threshold2"] = dev2 * 0.8
        start = input("What time of day do you want to start exercising [0-24]:")
        end = input("When do you want to end [0-24]: ")
        interval = input("How long do you want your intervals to be (in mins): ")
        user["start"] = int(start)
        user["end"] = int(end)
        user["interval"] = int(interval)
        return user

    def calibrate_thresholds(self):
        raise NotImplementedError

    def update_user(self):
        self.users[self.username] = self.user
        with open(USERS_JSON, "w") as file:
            json.dump(self.users, file)

    def master_function(self):
        # Uncomment this line if you want to ask user.
        #self.prompt_user()
        
        while True:
            self.username = default_user
            self.user = self.users[self.username]
            if dt(dt.now().year, dt.now().month, dt.now().day,self.user["start"])< dt.now() < dt(dt.now().year, dt.now().month, dt.now().day,self.user["end"]):
                print(f"Greetings {self.username}. Your credit score is: {self.user['score']}")
                added_score = get_score(self.user["threshold0"], self.user["threshold1"], self.user["threshold2"], mode=2)
                print(f"Congrats for the exercise. \nYou have now obtained {added_score} credits!")
                self.user["score"] += added_score
                self.update_user()
                time.sleep(self.user["interval"] * 60)

if __name__ == "__main__":
    exercise = Exercise()
    exercise.master_function()