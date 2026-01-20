# MMC (Main Mission Computer) – OpenAPI 3.1 Specification

This document defines the MMC interface orders as REST/JSON endpoints in OpenAPI 3.1.
All messages use **POST** requests with **JSON** payloads, except where noted.

## OpenAPI 3.1

```yaml
openapi: 3.1.0
info:
	title: MMC Interface Orders
	version: 1.0.0
	description: >-
		OpenAPI specification for MMC message orders between BMC, MUC, and Turret.
servers:
	- url: http://localhost:8080
		description: Local development server

paths:
	/bmc/target:
		post:
			summary: MMC ➜ BMC Target Message
			description: Provide target kinematics to BMC.
			requestBody:
				required: true
				content:
					application/json:
						schema:
							$ref: '#/components/schemas/TargetMessage'
						examples:
							example:
								value:
									target_id: 7
									position_north: 1250.5
									position_east: -340.2
									position_down: 50.0
									velocity_north: 120.0
									velocity_east: 5.5
									velocity_down: -2.0
			responses:
				'200':
					description: Accepted
					content:
						application/json:
							schema:
								$ref: '#/components/schemas/Ack'

	/bmc/fire-command:
		post:
			summary: BMC ➜ MMC Fire Command
			description: Instruct MMC to fire or not fire at a specific target.
			requestBody:
				required: true
				content:
					application/json:
						schema:
							$ref: '#/components/schemas/FireCommand'
						examples:
							example:
								value:
									fire_command: YES
									target_id: 7
			responses:
				'200':
					description: Accepted
					content:
						application/json:
							schema:
								$ref: '#/components/schemas/Ack'

	/bmc/status:
		post:
			summary: MMC ➜ BMC Status
			description: Report launcher readiness state.
			requestBody:
				required: true
				content:
					application/json:
						schema:
							$ref: '#/components/schemas/MissileLockStatus'
						examples:
							example:
								value:
									is_missile_lock: true
			responses:
				'200':
					description: Accepted
					content:
						application/json:
							schema:
								$ref: '#/components/schemas/Ack'

	/muc/lock-command:
		post:
			summary: MMC ➜ MUC Lock Command
			description: Request MUC to initiate or release missile lock process.
			requestBody:
				required: true
				content:
					application/json:
						schema:
							$ref: '#/components/schemas/LockCommand'
						examples:
							example:
								value:
									lock_command: LOCK
			responses:
				'200':
					description: Accepted
					content:
						application/json:
							schema:
								$ref: '#/components/schemas/Ack'

	/muc/lock-status:
		post:
			summary: MUC ➜ MMC Missile Lock Status
			description: Report whether missile lock has been achieved.
			requestBody:
				required: true
				content:
					application/json:
						schema:
							$ref: '#/components/schemas/MissileLockStatus'
						examples:
							example:
								value:
									is_missile_lock: false
			responses:
				'200':
					description: Accepted
					content:
						application/json:
							schema:
								$ref: '#/components/schemas/Ack'

	/turret/azimuth-command:
		post:
			summary: MMC ➜ Turret Azimuth Command
			description: Command turret azimuth in degrees.
			requestBody:
				required: true
				content:
					application/json:
						schema:
							$ref: '#/components/schemas/AzimuthCommand'
						examples:
							example:
								value:
									azimuth_command: 135
			responses:
				'200':
					description: Accepted
					content:
						application/json:
							schema:
								$ref: '#/components/schemas/Ack'

	/turret/azimuth-status:
		get:
			summary: MMC ➜ Turret Current Turret Azimuth
			description: Fetch current turret azimuth in degrees.
			responses:
				'200':
					description: OK
					content:
						application/json:
							schema:
								$ref: '#/components/schemas/AzimuthStatus'

components:
	schemas:
		Ack:
			type: object
			additionalProperties: false
			properties:
				status:
					type: string
					enum: [OK]
			required: [status]

		TargetId:
			type: integer
			minimum: 0
			description: Unique target identifier.

		FireCommandType:
			type: string
			enum: [YES, NO]
			description: Fire authorization.

		LockCommandType:
			type: string
			enum: [LOCK, NO_LOCK]
			description: Lock command for MUC.

		MissileLockStatus:
			type: object
			additionalProperties: false
			properties:
				is_missile_lock:
					type: boolean
					description: True when missile lock is achieved.
			required: [is_missile_lock]

		TargetKinematics:
			type: object
			additionalProperties: false
			properties:
				position_north:
					type: number
					description: Position north (meters).
				position_east:
					type: number
					description: Position east (meters).
				position_down:
					type: number
					description: Position down (meters).
				velocity_north:
					type: number
					description: Velocity north (meters per second).
				velocity_east:
					type: number
					description: Velocity east (meters per second).
				velocity_down:
					type: number
					description: Velocity down (meters per second).
			required:
				- position_north
				- position_east
				- position_down
				- velocity_north
				- velocity_east
				- velocity_down

		TargetMessage:
			allOf:
				- type: object
					additionalProperties: false
					properties:
						target_id:
							$ref: '#/components/schemas/TargetId'
					required: [target_id]
				- $ref: '#/components/schemas/TargetKinematics'

		FireCommand:
			type: object
			additionalProperties: false
			properties:
				fire_command:
					$ref: '#/components/schemas/FireCommandType'
				target_id:
					$ref: '#/components/schemas/TargetId'
			required: [fire_command, target_id]

		LockCommand:
			type: object
			additionalProperties: false
			properties:
				lock_command:
					$ref: '#/components/schemas/LockCommandType'
			required: [lock_command]

		AzimuthDegrees:
			type: integer
			minimum: 0
			maximum: 359
			description: Azimuth in degrees (0-359).

		AzimuthCommand:
			type: object
			additionalProperties: false
			properties:
				azimuth_command:
					$ref: '#/components/schemas/AzimuthDegrees'
			required: [azimuth_command]

		AzimuthStatus:
			type: object
			additionalProperties: false
			properties:
				current_azimuth:
					$ref: '#/components/schemas/AzimuthDegrees'
			required: [current_azimuth]
```
