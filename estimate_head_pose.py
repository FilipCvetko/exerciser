"""Demo code shows how to estimate human head pose.
Currently, human face is detected by a detector from an OpenCV DNN module.
Then the face box is modified a little to suits the need of landmark
detection. The facial landmark detection is done by a custom Convolutional
Neural Network trained with TensorFlow. After that, head pose is estimated
by solving a PnP problem.
"""
from argparse import ArgumentParser
from multiprocessing import Process, Queue

import cv2
import numpy as np
from config import *

from mark_detector import MarkDetector
from os_detector import detect_os
from pose_estimator import PoseEstimator
from stabilizer import Stabilizer

print("OpenCV version: {}".format(cv2.__version__))

# multiprocessing may not work on Windows and macOS, check OS for safety.
detect_os()

CNN_INPUT_SIZE = 128

# Take arguments from user input.
parser = ArgumentParser()
parser.add_argument("--video", type=str, default=None,
                    help="Video file to be processed.")
parser.add_argument("--cam", type=int, default=None,
                    help="The webcam index.")
args = parser.parse_args()


def get_face(detector, img_queue, box_queue):
    """Get face from image queue. This function is used for multiprocessing"""
    while True:
        image = img_queue.get()
        box = detector.extract_cnn_facebox(image)
        box_queue.put(box)

def main():
    """MAIN"""
    # Video source from webcam or video file.
    video_src = args.cam if args.cam is not None else args.video
    if video_src is None:
        print("Warning: video source not assigned, default webcam will be used.")
        video_src = 0

    cap = cv2.VideoCapture(video_src)
    if video_src == 0:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    _, sample_frame = cap.read()

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

    while True:
        # Read frame, crop it, flip it, suits your needs.
        frame_got, frame = cap.read()
        if frame_got is False:
            break

        if cv2.waitKey(33) == 27:
            # Escape pressed
            return int(score)

        # Crop it if frame is larger than expected.
        # frame = frame[0:480, 300:940]

        # If frame comes from webcam, flip it so it looks like a mirror.
        if video_src == 0:
            frame = cv2.flip(frame, 2)

        # Pose estimation by 3 steps:
        # 1. detect face;
        # 2. detect landmarks;
        # 3. estimate pose

        # Feed frame to image queue.
        img_queue.put(frame)

        # Get face from box queue.
        facebox = box_queue.get()

        if facebox is not None:
            # Detect landmarks from image of 128x128.
            face_img = frame[facebox[1]: facebox[3],
                             facebox[0]: facebox[2]]
            face_img = cv2.resize(face_img, (CNN_INPUT_SIZE, CNN_INPUT_SIZE))
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

            print(score)
            
            if len(list0) % 5 == 0:
                dev0 = max(list0) - min(list0)
                dev1 = max(list1) - min(list1)
                dev2 = max(list2) - min(list2)
                
                if flag0 == False and dev0 > threshold0:
                    print("You have rotated head left and right! Congrats!")
                    score += reward_head_task
                    flag0 = True
		        
                if flag1 == False and dev1 > threshold1:
                    print("You have moved head forwards and backwards! Congrats!")
                    score += reward_head_task
                    flag1 = True
		        
                if flag2 == False and dev2 > threshold2:
                    print("You have tilted head left and right! Congrats!")
                    score += reward_head_task
                    flag2 = True
                    
                if flag0 and flag1 and flag2:
                    print("ALL HEAD TASKS COMPLETED")
                    return int(score)
            
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
            # pose_estimator.draw_annotation_box(
            #     frame, pose[0], pose[1], color=(255, 128, 128))

            # Uncomment following line to draw stabile pose annotation on frame.
            pose_estimator.draw_annotation_box(
                frame, steady_pose[0], steady_pose[1], color=(128, 255, 128))

            # Uncomment following line to draw head axes on frame.
            # pose_estimator.draw_axes(frame, steady_pose[0], steady_pose[1])

        # Show preview.
        cv2.imshow("Preview", frame)
        if cv2.waitKey(10) == 27:
            break

    # Clean up the multiprocessing process.
    box_process.terminate()
    box_process.join()


if __name__ == '__main__':
    main()
