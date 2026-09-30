# Profiles

Profiles are stored beneath the platform data directory returned by `platformdirs`. Each is marked with `.pbb-profile`; deletion refuses unmarked directories. Browser data may include authentication state, so protect it as sensitive local data.

PBB's `profile.lock` records process ID and process start time. `pbb recover` removes it only when the owning process no longer exists. It never changes Edge or Chrome native lock files.

