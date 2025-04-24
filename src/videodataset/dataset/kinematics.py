import pinocchio as pin  # type: ignore[import-untyped]
import numpy as np
from scipy.optimize import minimize  # type: ignore[import-untyped]
import quaternionic  # type: ignore[import-untyped]
from scipy.spatial.transform import Rotation as R  # type: ignore[import-untyped]


class Kinematics:
    def __init__(self, urdf_path):
        # 加载URDF模型
        self.model = pin.buildModelFromUrdf(urdf_path)
        self.data = self.model.createData()

        # 设置关节限位
        self.bounds = []
        for i in range(2, 16):
            self.bounds.append(
                (self.model.lowerPositionLimit[i], self.model.upperPositionLimit[i])
            )
            # print("lower upper limit: ", self.model.lowerPositionLimit[i], self.model.upperPositionLimit[i])

        print("boundsssssss", self.bounds)

        # 打印模型总关节，包括不能动的关节
        print(f"模型总关节数: {self.model.njoints}")
        print("模型中的所有关节:")
        for i in range(self.model.njoints):
            print(f"Joint {i}: {self.model.names[i]}")

        # 获取左右臂的关节名称
        self.left_joint_names = [f"Joint{i}_l" for i in range(1, 8)]
        self.right_joint_names = [f"Joint{i}_r" for i in range(1, 8)]

        # 获取左右臂的关节ID
        try:
            self.left_joint_ids = [
                self.model.getJointId(name) for name in self.left_joint_names
            ]
        except Exception as e:
            print(f"错误: 找不到 'Joint{i}_l' 关节: {str(e)}")
            self.left_joint_ids = []
        try:
            self.right_joint_ids = [
                self.model.getJointId(name) for name in self.right_joint_names
            ]
        except Exception as e:
            print(f"错误: 找不到 'Joint{i}_r' 关节: {str(e)}")
            self.right_joint_ids = []

        # 打印所有可用的 frame 名称和对应的 ID
        print("\n所有可用的 frames:")
        for frame_id in range(self.model.nframes):
            frame_name = self.model.frames[frame_id].name
            print(f"Frame {frame_id}: {frame_name}")

        # 获取基座和末端执行器的frame ID
        try:
            self.arm_base_frame_id = self.model.getFrameId("link-arm")
            print(
                f"\n基座 frame ID: {self.arm_base_frame_id}, 名称: {self.model.frames[self.arm_base_frame_id].name}"
            )
        except Exception as e:
            print(f"错误: 找不到 'link-arm' frame: {str(e)}")
            self.arm_base_frame_id = None

        try:
            self.left_ee_frame_id = self.model.getFrameId("Link7_l")
            print(
                f"左臂末端 frame ID: {self.left_ee_frame_id}, 名称: {self.model.frames[self.left_ee_frame_id].name}"
            )
        except Exception as e:
            print(f"错误: 找不到 'Link7_l' frame: {str(e)}")
            self.left_ee_frame_id = None

        try:
            self.right_ee_frame_id = self.model.getFrameId("Link7_r")
            print(
                f"右臂末端 frame ID: {self.right_ee_frame_id}, 名称: {self.model.frames[self.right_ee_frame_id].name}"
            )
        except Exception as e:
            print(f"错误: 找不到 'Link7_r' frame: {str(e)}")
            self.right_ee_frame_id = None

        # 验证左右臂末端 frame ID 是否不同
        if (
            self.left_ee_frame_id == self.right_ee_frame_id
            and self.left_ee_frame_id is not None
        ):
            raise ValueError(
                f"左右臂末端 frame ID 相同 ({self.left_ee_frame_id})！请检查 URDF 文件中的 frame 名称。"
            )

        self.pos_error_weight = 60.0
        self.ori_error_weight = 20.0
        self.vel_error_weight = 0.0
        self.max_iterations = 500
        self.error_tol = 1e-7

    def update_pos_error_weight(self, weight):
        self.pos_error_weight = weight

    def update_ori_error_weight(self, weight):
        self.ori_error_weight = weight

    def update_vel_error_weight(self, weight):
        self.vel_error_weight = weight

    def update_max_iterations(self, max_iter):
        self.max_iterations = max_iter

    def update_error_tol(self, error_tol):
        self.error_tol = error_tol

    def rpy_to_quaternion(self, roll, pitch, yaw):
        # 使用 RPY 构造旋转
        r = R.from_euler("xyz", [roll, pitch, yaw], degrees=False)
        # 获取四元数，格式为 (x, y, z, w)
        quat = r.as_quat()
        return quat

    def quaternion_to_rpy(self, x, y, z, w):
        # 使用四元数创建旋转对象
        r = R.from_quat([x, y, z, w])
        # 将旋转对象转为欧拉角 (roll, pitch, yaw)
        rpy = r.as_euler("xyz", degrees=False)  # 'xyz' 指定顺序，返回弧度值
        return rpy

    def compute_arm_fk(self, arm_joint_angles, waist_pitch_value, waist_lift_value):
        if len(arm_joint_angles) != 14:
            raise ValueError(f"传入的关节角度数量 ({len(arm_joint_angles)}) 不是14")

        # Reuse pre-allocated zero vector instead of creating new one
        q = np.array(arm_joint_angles)

        waist_joints = np.array([waist_lift_value, waist_pitch_value])
        # head_joints = np.array([self.head_pitch_value, self.head_yaw_value])
        head_joints = np.zeros(2)
        total_q = np.concatenate([waist_joints, q, head_joints])

        # Compute FK only once and store results
        pin.forwardKinematics(self.model, self.data, total_q)
        pin.updateFramePlacements(self.model, self.data)

        # 获取左臂末端位姿
        left_pose = pin.SE3ToXYZQUAT(self.data.oMf[self.left_ee_frame_id])
        left_pose_rpy = self.quaternion_to_rpy(*left_pose[3:])
        left_pose = np.array(
            [
                left_pose[0],
                left_pose[1],
                left_pose[2],
                left_pose_rpy[0],
                left_pose_rpy[1],
                left_pose_rpy[2],
            ]
        )
        # 获取右臂末端位姿
        right_pose = pin.SE3ToXYZQUAT(self.data.oMf[self.right_ee_frame_id])
        right_pose_rpy = self.quaternion_to_rpy(*right_pose[3:])
        right_pose = np.array(
            [
                right_pose[0],
                right_pose[1],
                right_pose[2],
                right_pose_rpy[0],
                right_pose_rpy[1],
                right_pose_rpy[2],
            ]
        )
        return left_pose, right_pose

    def compute_jacobian(self, joint_angles):
        """计算左右臂末端执行器的雅可比矩阵

        Args:
            joint_angles: 包含所有关节角度的数组

        Returns:
            left_jacobian: 左臂末端执行器的雅可比矩阵 (6xn)
            right_jacobian: 右臂末端执行器的雅可比矩阵 (6xn)
        """
        # 更新机器人状态
        q = np.array(joint_angles)
        pin.forwardKinematics(self.model, self.data, q)
        pin.updateFramePlacements(self.model, self.data)

        # 计算左臂末端执行器的雅可比矩阵
        left_jacobian = pin.computeFrameJacobian(
            self.model,
            self.data,
            q,
            self.left_ee_frame_id,
            pin.ReferenceFrame.LOCAL_WORLD_ALIGNED,
        )

        # 计算右臂末端执行器的雅可比矩阵
        right_jacobian = pin.computeFrameJacobian(
            self.model,
            self.data,
            q,
            self.right_ee_frame_id,
            pin.ReferenceFrame.LOCAL_WORLD_ALIGNED,
        )

        left_ee_pose = self.data.oMf[self.left_ee_frame_id]
        right_ee_pose = self.data.oMf[self.right_ee_frame_id]
        return left_jacobian, right_jacobian, left_ee_pose, right_ee_pose

    def compute_arm_ik(
        self,
        init_arm_joint_angles,
        waist_pitch_value,
        waist_lift_value,
        left_target_pose,
        right_target_pose,
    ):
        def _fi(n, s, c, r, x):
            dx = x - s
            exp_term = np.exp(-(dx**2) / (2 * c**2))
            return (-1) ** n * exp_term + r * (dx**4)

        def _position_cost(left_target, right_target, left_actual, right_actual):
            n, s, c, r = 1, 0, 0.2, 5.0
            xl = np.linalg.norm(left_target - left_actual)
            xr = np.linalg.norm(right_target - right_actual)
            return _fi(n, s, c, r, xl) + _fi(n, s, c, r, xr)

        def _orientation_cost(
            left_target_quat, right_target_quat, left_actual_quat, right_actual_quat
        ):
            n, s, c, r = 1, 0, 0.2, 5.0
            xl = quaternionic.distance.rotation.intrinsic(
                quaternionic.array(left_target_quat),
                quaternionic.array(left_actual_quat),
            )
            xr = quaternionic.distance.rotation.intrinsic(
                quaternionic.array(right_target_quat),
                quaternionic.array(right_actual_quat),
            )
            return _fi(n, s, c, r, xl) + _fi(n, s, c, r, xr)

        def _joint_velocity_cost(current_q, new_q):
            n, s, c, r = 1, 0, 0.2, 5.0
            # 左臂关节速度代价
            left_diff = current_q[0:7] - new_q[0:7]
            left_diff[0] *= 2.0
            left_diff[1] *= 2.0
            left_diff[2] *= 2.0
            left_diff[3] *= 2.0
            left_diff[5] *= 1.5
            xl = np.linalg.norm(left_diff)

            # 右臂关节速度代价
            right_diff = current_q[7:14] - new_q[7:14]
            right_diff[0] *= 2.0
            right_diff[1] *= 2.0
            right_diff[2] *= 2.0
            right_diff[3] *= 2.0
            right_diff[5] *= 1.5
            xr = np.linalg.norm(right_diff)

            return _fi(n, s, c, r, xl) + _fi(n, s, c, r, xr)

        # Cache numpy arrays instead of creating new ones in cost function
        left_target_pos = left_target_pose[:3]
        right_target_pos = right_target_pose[:3]

        left_target_quat = quaternionic.array(
            self.rpy_to_quaternion(*left_target_pose[3:])
        )
        right_target_quat = quaternionic.array(
            self.rpy_to_quaternion(*right_target_pose[3:])
        )

        def _cost(q):
            left_current, right_current = self.compute_arm_fk(
                q, waist_pitch_value, waist_lift_value
            )
            left_current_quat = quaternionic.array(
                self.rpy_to_quaternion(*left_current[3:])
            )
            right_current_quat = quaternionic.array(
                self.rpy_to_quaternion(*right_current[3:])
            )

            # Use pre-computed arrays
            pos_cost = _position_cost(
                left_target_pos, right_target_pos, left_current[:3], right_current[:3]
            )

            ori_cost = _orientation_cost(
                left_target_quat,
                right_target_quat,
                left_current_quat,
                right_current_quat,
            )

            vel_cost = _joint_velocity_cost(init_arm_joint_angles, q)

            return (
                self.pos_error_weight * pos_cost
                + self.ori_error_weight * ori_cost
                + self.vel_error_weight * vel_cost
            )

        # 使用SLSQP优化器求解
        result = minimize(
            _cost,
            init_arm_joint_angles,
            method="L-BFGS-B",
            tol=self.error_tol,
            bounds=self.bounds,
            options={"maxiter": self.max_iterations},
        )

        if result.success:
            # print(f"IK求解成功,最终误差:{result.fun}")
            return result.x.tolist()
        else:
            print(f"IK求解失败:{result.message}")
            return None

    def compute_collision(self, arm_joint_angles):
        return False


if __name__ == "__main__":
    from pathlib import Path

    kinematics = Kinematics((Path(__file__).parent / "urdf/A2D_viz.urdf").as_posix())

    init_arm_joint_angles = [
        -0.98404,
        0.83978,
        1.379,
        -0.53439,
        2.6041,
        -0.56746,
        0.33719,
        0.83631,
        -1.0087,
        0.22746,
        0.59724,
        -1.6914,
        -1.25,
        -0.87571,
    ]
    waist_pitch = 0.4
    waist_lift = 0.2
    fk_left_pose, fk_right_pose = kinematics.compute_arm_fk(
        init_arm_joint_angles,
        waist_pitch,
        waist_lift,
    )
    print("fk_left_pose: ", fk_left_pose)
    print("fk_right_pose: ", fk_right_pose)

    ik_result = kinematics.compute_arm_ik(
        [
            -0.90134,
            0.83978,
            1.379,
            -0.53439,
            2.6041,
            -0.56746,
            0.33719,
            0.83631,
            -1.0087,
            0.22746,
            0.59724,
            -1.6914,
            -1.25,
            -0.87571,
        ],
        waist_pitch,
        waist_lift,
        fk_left_pose,
        fk_right_pose,
    )
    print("init_arm_joint_angles: ", init_arm_joint_angles)
    print("ik_result: ", ik_result)

    ik_left_pose, ik_right_pose = kinematics.compute_arm_fk(
        ik_result, waist_pitch, waist_lift
    )
    print("ik_left_pose: ", ik_left_pose)
    print("ik_right_pose: ", ik_right_pose)
