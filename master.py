from stabilizer import Stabilizer
from config import *
import json
import time
import numpy as np
from multiprocessing import Process, Queue

from datetime import datetime as dt
from estimate_head_pose import get_score, get_face
import cv2
import PySimpleGUI as sg
from mark_detector import MarkDetector
from os_detector import detect_os
from pose_estimator import PoseEstimator
from stabilizer import Stabilizer


class Exercise():
    def __init__(self):
        self.users = None
        self.username = None
        self.user = None
        with open(USERS_JSON, "r") as file:
            self.users = json.load(file)
        self.video_capture = cv2.VideoCapture(0)
        self.CNN_INPUT_SIZE = 128

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
        self.username = default_user
        self.user = self.users[self.username]
        #print(f"Greetings {self.username}. Your credit score is: {self.user['score']}")

        # GUI layout
        left = [
            [sg.Text("Filip Cvetko")],
            [sg.Text(f"Credits: {self.user['score']}")],
            [sg.Image(key="-IMAGE-")],
            [sg.Text("", key="-FINISHED-")]
        ]

        # layout = [
        #     [
        #         sg.Column(left),
        #         sg.VSeparator(),
        #         sg.Column(right),
        #     ]
        # ]

        window = sg.Window(title="Exerciser", layout=left, resizable=True)

        _, sample_frame = self.video_capture.read()
        # Introduce mark_detector to detect landmarks.
        mark_detector = MarkDetector()

        # Setup process and queues for multiprocessing.
        img_queue = Queue()
        box_queue = Queue()
        img_queue.put(sample_frame)
        box_process = Process(target=get_face, args=(
            mark_detector, img_queue, box_queue,))
        box_process.start()

        # Introduce pose estimator to solve pose. Get one frame to setup the
        # estimator according to the image size.
        print(sample_frame.shape)
        height, width = sample_frame.shape[:2]
        pose_estimator = PoseEstimator(img_size=(height, width))

        # Introduce scalar stabilizers for pose.
        pose_stabilizers = [Stabilizer(
            state_num=2,
            measure_num=1,
            cov_process=0.1,
            cov_measure=0.1) for _ in range(6)]

        tm = cv2.TickMeter()
        
        list0 = []
        list1 = []
        list2 = []

        flag0 = False
        flag1 = False
        flag2 = False

        score = 0

        # EVENT HANDLER
        while True:
            event, values = window.read(timeout=20)

            if event == sg.WIN_CLOSED:
                break

            ret, frame = self.video_capture.read()
            frame = cv2.flip(frame, 2)
            if ret is False:
                break

            # Feed frame to image queue.
            img_queue.put(frame)

            # Get face from box queue.
            facebox = box_queue.get()

            if facebox is not None:
                # Detect landmarks from image of 128x128.
                face_img = frame[facebox[1]: facebox[3],
                                facebox[0]: facebox[2]]
                face_img = cv2.resize(face_img, (self.CNN_INPUT_SIZE, self.CNN_INPUT_SIZE))
                face_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)

                tm.start()
                marks = mark_detector.detect_marks(face_img)
                tm.stop()

                # Convert the marks locations from local CNN to global image.
                marks *= (facebox[2] - facebox[0])
                marks[:, 0] += facebox[0]
                marks[:, 1] += facebox[1]

                # Uncomment following line to show raw marks.
                # mark_detector.draw_marks(frame, marks, color=(0, 255, 0))

                # Uncomment following line to show facebox.
                # mark_detector.draw_box(frame, [facebox])

                # Try pose estimation with 68 points.
                pose = pose_estimator.solve_pose_by_68_points(marks)
                
                list0.append(float(pose[0][0]))
                list1.append(float(pose[0][1]))
                list2.append(float(pose[0][2]))
                
                if len(list0) % 5 == 0:
                    dev0 = max(list0) - min(list0)
                    dev1 = max(list1) - min(list1)
                    dev2 = max(list2) - min(list2)

                    if flag0 == False and dev0 > self.user["threshold0"]:
                        print("You have rotated head left and right! Congrats!")
                        score += reward_head_task
                        flag0 = True
                    
                    if flag1 == False and dev1 > self.user["threshold1"]:
                        print("You have moved head forwards and backwards! Congrats!")
                        score += reward_head_task
                        flag1 = True
                    
                    if flag2 == False and dev2 > self.user["threshold2"]:
                        print("You have tilted head left and right! Congrats!")
                        score += reward_head_task
                        flag2 = True
                        
                    if flag0 and flag1 and flag2:
                        window["-FINISHED-"].update("ALL HEAD TASKS COMPLETED")
                        time.sleep(2)
                        cv2.destroyAllWindows()
                        break

                
                
                # pose[0] = left, right rotation
                # pose[1] = flexion, extension upward or backward
                # pose[2] = lateral flexion
                
                
                
                # Stabilize the pose.
                steady_pose = []
                pose_np = np.array(pose).flatten()
                for value, ps_stb in zip(pose_np, pose_stabilizers):
                    ps_stb.update([value])
                    steady_pose.append(ps_stb.state[0])
                steady_pose = np.reshape(steady_pose, (-1, 3))

                # Uncomment following line to draw pose annotation on frame.
                pose_estimator.draw_annotation_box(
                    frame, pose[0], pose[1], color=(255, 128, 128))

                # Uncomment following line to draw stabile pose annotation on frame.
                #pose_estimator.draw_annotation_box(
                #    frame, steady_pose[0], steady_pose[1], color=(128, 255, 128))

                # Uncomment following line to draw head axes on frame.
                # pose_estimator.draw_axes(frame, steady_pose[0], steady_pose[1])



            imgbytes = cv2.imencode(".png", frame)[1].tobytes()
            window["-IMAGE-"].update(data=imgbytes)
            if cv2.waitKey(10) == 27:
                cv2.destroyAllWindows()
                break

        box_process.terminate()
        box_process.join()

        print(f"Congrats for the exercise. \nYou have now obtained {score} credits!")
        self.user["score"] += score
        self.update_user()


        self.video_capture.release()
        cv2.destroyAllWindows()

       


if __name__ == "__main__":
    exercise = Exercise()
    exercise.master_function()