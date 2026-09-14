import time

import cv2
import rclpy
from cv_bridge import CvBridge
from diagnostic_msgs.msg import (
    DiagnosticArray,
    DiagnosticStatus,
    KeyValue,
)
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import Float32, String
from visualization_msgs.msg import Marker, MarkerArray

from . import config
from .audio_alert import trigger_alert
from .depth_source import estimate_xyz, get_distance, reset_history
from .detector import detect_people
from .dwell_tracker import clear_state as clear_dwell
from .dwell_tracker import update as update_dwell
from .logger import SessionLogger
from .overlay import draw_boxes, draw_breach_text, draw_info_panel
from .proximity import clear_state, evaluate_proximity
from .screenshot import ScreenshotManager


class ROS2ProximityNode(Node):
    def __init__(self):
        super().__init__("ros2_proximity_node")

        self.bridge = CvBridge()

        self.latest_color = None
        self.latest_depth = None
        self.latest_color_stamp_ns = None
        self.latest_depth_stamp_ns = None
        self.camera_info = None
        self.camera_frame_id = config.CAMERA_FRAME_ID

        self.previous_ids = set()
        self.previous_frame_time = time.monotonic()
        self.last_fps = 0.0
        self.processing = False

        self.color_sub = self.create_subscription(
            Image,
            config.COLOR_TOPIC,
            self.color_callback,
            10,
        )

        self.depth_sub = self.create_subscription(
            Image,
            config.ALIGNED_DEPTH_TOPIC,
            self.depth_callback,
            10,
        )

        self.camera_info_sub = self.create_subscription(
            CameraInfo,
            config.CAMERA_INFO_TOPIC,
            self.camera_info_callback,
            10,
        )

        self.safety_pub = self.create_publisher(
            String,
            "/safety_status",
            10,
        )

        self.distance_pub = self.create_publisher(
            Float32,
            "/human_distance",
            10,
        )

        self.overlay_pub = self.create_publisher(
            Image,
            "/camera_overlay",
            10,
        )

        self.marker_pub = self.create_publisher(
            MarkerArray,
            "/human_markers",
            10,
        )

        self.diagnostics_pub = self.create_publisher(
            DiagnosticArray,
            "/diagnostics",
            10,
        )

        self.session_logger = SessionLogger()
        self.screenshot_manager = ScreenshotManager()

        if config.SHOW_OPENCV_WINDOW:
            cv2.namedWindow(
                config.WINDOW_NAME,
                cv2.WINDOW_NORMAL,
            )
            cv2.resizeWindow(
                config.WINDOW_NAME,
                config.WINDOW_WIDTH,
                config.WINDOW_HEIGHT,
            )

        self.timer = self.create_timer(
            1.0 / config.FPS_TARGET,
            self.process_frame,
        )

        self.get_logger().info(
            "ROS2 Human Proximity Monitor started."
        )

    def color_callback(self, message):
        try:
            self.latest_color = self.bridge.imgmsg_to_cv2(
                message,
                desired_encoding="bgr8",
            )
            self.latest_color_stamp_ns = (
                message.header.stamp.sec * 1_000_000_000
                + message.header.stamp.nanosec
            )

            if message.header.frame_id:
                self.camera_frame_id = message.header.frame_id

        except Exception as error:
            self.get_logger().error(
                f"RGB conversion failed: {error}"
            )

    def depth_callback(self, message):
        try:
            self.latest_depth = self.bridge.imgmsg_to_cv2(
                message,
                desired_encoding="passthrough",
            )
            self.latest_depth_stamp_ns = (
                message.header.stamp.sec * 1_000_000_000
                + message.header.stamp.nanosec
            )

        except Exception as error:
            self.get_logger().error(
                f"Depth conversion failed: {error}"
            )

    def camera_info_callback(self, message):
        self.camera_info = message

        if message.header.frame_id:
            self.camera_frame_id = message.header.frame_id

    def process_frame(self):
        if self.processing:
            return

        if self.latest_color is None or self.latest_depth is None:
            return

        if self.camera_info is None:
            return

        if self.latest_color_stamp_ns is None:
            return

        if self.latest_depth_stamp_ns is None:
            return

        timestamp_difference_ns = abs(
            self.latest_color_stamp_ns - self.latest_depth_stamp_ns
        )

        if timestamp_difference_ns > 150_000_000:
            return

        self.processing = True

        try:
            color_frame = self.latest_color.copy()
            depth_image = self.latest_depth.copy()

            people = detect_people(color_frame)

            current_ids = {person["id"] for person in people}

            for lost_id in self.previous_ids - current_ids:
                reset_history(lost_id)
                clear_state(lost_id)
                clear_dwell(lost_id)

            self.previous_ids = current_ids

            invalid_depth_count = 0

            for person in people:
                distance = get_distance(
                    person["id"],
                    person["bbox"],
                    depth_image,
                )

                person["distance"] = distance

                if distance is None:
                    invalid_depth_count += 1
                    self.session_logger.log_system_event(
                        "invalid_depth",
                        f"person_id={person['id']}",
                    )
                    continue

                person["xyz"] = estimate_xyz(
                    person["bbox"],
                    distance,
                    self.camera_info,
                )

            people = evaluate_proximity(people)

            for person in people:
                person["dwell_seconds"] = update_dwell(
                    person["id"],
                    person["zone"],
                )

            now = time.monotonic()
            elapsed = now - self.previous_frame_time

            if elapsed > 0.0:
                self.last_fps = 1.0 / elapsed

            self.previous_frame_time = now

            any_breach = any(
                person.get("is_breach", False)
                for person in people
            )

            closest_distance = self._get_closest_distance(people)

            draw_boxes(color_frame, people)
            draw_info_panel(
                color_frame,
                self.last_fps,
                len(people),
            )
            draw_breach_text(color_frame, any_breach)

            self.session_logger.next_frame(len(people))

            for person in people:
                if not person.get("is_breach", False):
                    continue

                trigger_alert(person["distance"])

                self.session_logger.log_breach(
                    person["id"],
                    person["distance"],
                    person["zone"],
                    person["dwell_seconds"],
                )

            self.screenshot_manager.check_and_capture(
                color_frame,
                closest_distance,
                self.last_fps,
                any_breach,
            )

            self.publish_safety_status(people)
            self.publish_overlay(color_frame)
            self.publish_markers(people)
            self.publish_diagnostics(
                people,
                invalid_depth_count,
                any_breach,
            )

            if config.SHOW_OPENCV_WINDOW:
                cv2.imshow(config.WINDOW_NAME, color_frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    self.get_logger().info(
                        "Quit requested. Shutting down."
                    )
                    rclpy.shutdown()

        except Exception as error:
            self.get_logger().error(
                f"Frame processing failed: "
                f"{type(error).__name__}: {error}"
            )
            self.session_logger.log_system_event(
                "processing_error",
                f"{type(error).__name__}: {error}",
            )

        finally:
            self.processing = False

    @staticmethod
    def _valid_people(people):
        return [
            person
            for person in people
            if person.get("distance") is not None
        ]

    def _get_closest_distance(self, people):
        valid_people = self._valid_people(people)

        if not valid_people:
            return None

        return min(
            person["distance"]
            for person in valid_people
        )

    def publish_safety_status(self, people):
        valid_people = self._valid_people(people)

        if not valid_people:
            self.safety_pub.publish(
                String(data="NO_VALID_DEPTH | no valid human depth")
            )
            self.distance_pub.publish(Float32(data=-1.0))
            return

        closest = min(
            valid_people,
            key=lambda person: person["distance"],
        )

        any_breach = any(
            person.get("is_breach", False)
            for person in valid_people
        )

        system_state = (
            "PROXIMITY_BREACH"
            if any_breach
            else "SAFE"
        )

        xyz = closest.get("xyz")

        if xyz is None:
            xyz_text = "xyz=unavailable"
        else:
            xyz_text = (
                f"x={xyz[0]:.3f},"
                f"y={xyz[1]:.3f},"
                f"z={xyz[2]:.3f}"
            )

        status_text = (
            f"{system_state} | "
            f"closest_id={closest['id']} | "
            f"distance_m={closest['distance']:.2f} | "
            f"{xyz_text}"
        )

        self.safety_pub.publish(String(data=status_text))
        self.distance_pub.publish(
            Float32(data=float(closest["distance"]))
        )

    def publish_overlay(self, frame):
        try:
            message = self.bridge.cv2_to_imgmsg(
                frame,
                encoding="bgr8",
            )
            message.header.stamp = self.get_clock().now().to_msg()
            message.header.frame_id = self.camera_frame_id
            self.overlay_pub.publish(message)

        except Exception as error:
            self.get_logger().error(
                f"Overlay publish failed: {error}"
            )

    def publish_markers(self, people):
        marker_array = MarkerArray()
        stamp = self.get_clock().now().to_msg()

        delete_all = Marker()
        delete_all.action = Marker.DELETEALL
        marker_array.markers.append(delete_all)

        for person in people:
            xyz = person.get("xyz")

            if xyz is None:
                continue

            x, y, z = xyz

            color = (
                (1.0, 0.0, 0.0)
                if person.get("is_breach", False)
                else (0.0, 1.0, 0.0)
            )

            marker = Marker()
            marker.header.frame_id = self.camera_frame_id
            marker.header.stamp = stamp
            marker.ns = "detected_humans"
            marker.id = int(person["id"])
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD

            marker.pose.position.x = float(x)
            marker.pose.position.y = float(y)
            marker.pose.position.z = float(z)
            marker.pose.orientation.w = 1.0

            marker.scale.x = 0.25
            marker.scale.y = 0.25
            marker.scale.z = 0.25

            marker.color.r = color[0]
            marker.color.g = color[1]
            marker.color.b = color[2]
            marker.color.a = 0.9

            marker_array.markers.append(marker)

            label = Marker()
            label.header.frame_id = self.camera_frame_id
            label.header.stamp = stamp
            label.ns = "human_labels"
            label.id = int(person["id"]) + 10000
            label.type = Marker.TEXT_VIEW_FACING
            label.action = Marker.ADD

            label.pose.position.x = float(x)
            label.pose.position.y = float(y)
            label.pose.position.z = float(z + 0.25)
            label.pose.orientation.w = 1.0

            label.scale.z = 0.15
            label.color.r = 1.0
            label.color.g = 1.0
            label.color.b = 1.0
            label.color.a = 1.0

            label.text = (
                f"ID: {person['id']}\n"
                f"XYZ: {x:.2f}, {y:.2f}, {z:.2f} m\n"
                f"{person.get('zone', 'SAFE')}"
            )

            marker_array.markers.append(label)

        self.marker_pub.publish(marker_array)

    def publish_diagnostics(
        self,
        people,
        invalid_depth_count,
        any_breach,
    ):
        message = DiagnosticArray()
        message.header.stamp = self.get_clock().now().to_msg()

        status = DiagnosticStatus()
        status.name = "hrc_proximity_monitor"
        status.hardware_id = "Intel_RealSense_D435i"

        if self.latest_color is None or self.latest_depth is None:
            status.level = DiagnosticStatus.WARN
            status.message = "waiting_for_camera_frames"
        elif self.camera_info is None:
            status.level = DiagnosticStatus.WARN
            status.message = "waiting_for_camera_info"
        else:
            status.level = DiagnosticStatus.OK
            status.message = "running"

        closest_distance = self._get_closest_distance(people)

        status.values = [
            KeyValue(
                key="fps",
                value=f"{self.last_fps:.2f}",
            ),
            KeyValue(
                key="people_count",
                value=str(len(people)),
            ),
            KeyValue(
                key="invalid_depth_count",
                value=str(invalid_depth_count),
            ),
            KeyValue(
                key="closest_distance_m",
                value=(
                    f"{closest_distance:.2f}"
                    if closest_distance is not None
                    else "-1.00"
                ),
            ),
            KeyValue(
                key="safety_state",
                value=(
                    "PROXIMITY_BREACH"
                    if any_breach
                    else "SAFE"
                ),
            ),
            KeyValue(
                key="color_topic",
                value=config.COLOR_TOPIC,
            ),
            KeyValue(
                key="depth_topic",
                value=config.ALIGNED_DEPTH_TOPIC,
            ),
        ]

        message.status.append(status)
        self.diagnostics_pub.publish(message)

    def destroy_node(self):
        self.session_logger.write_summary()

        if config.SHOW_OPENCV_WINDOW:
            cv2.destroyAllWindows()

        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)

    node = ROS2ProximityNode()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()