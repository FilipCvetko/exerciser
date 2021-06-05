from config import *
import json
from estimate_head_pose import main

class Exercise():
    def __init__(self):
        self.users = None
        self.username = None
        self.user = None
        with open(USERS_JSON, "r") as file:
            self.users = json.load(file)
        print(self.users)

    def prompt_user(self):
        print("-----------------------------\nWelcome to Exerciser. \nPlease tell me who you are: ")
        self.username = input()
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
        print(f"Greetings {self.username}. You have so far obtained {self.user['score']}")
        return self.user

    def exercise(self):
        added_score = main()
        print(added_score)
        return added_score

    def create_new_user(self):
        user = dict()
        user["score"] = 0
        user["threshold0"] = default_threshold0
        user["threshold1"] = default_threshold1
        user["threshold2"] = default_threshold2
        return user

    def calibrate_thresholds(self):
        raise NotImplementedError

    def update_user(self):
        self.users[self.username] = self.user
        with open(USERS_JSON, "w") as file:
            json.dump(self.users, file)

    def master_function(self):
        self.prompt_user()
        added_score = self.exercise()
        print(added_score)
        print(f"Congrats for the exercise. \n You have now obtained {added_score}")
        self.user["score"] += added_score
        self.update_user()
        return 1

exercise = Exercise()
exercise.master_function()