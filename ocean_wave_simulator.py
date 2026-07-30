#!/usr/bin/env python3
"""
Interactive 3D educational ocean simulator.

The model combines a directional wind sea, independent swell, finite-depth
gravity/capillary dispersion, lunar and solar equilibrium tides, current
Doppler shift, latitude-dependent Coriolis turning, inverse-barometer response,
storm surge, temperature/salinity-dependent density, viscosity, damping and a
simple seabed influence.

This is an exploratory visualization, not a navigation or forecast product.

Run:
    python3 ocean_wave_simulator.py

Controls:
    Drag the sliders, switch category tabs, drag the 3D view to rotate,
    Space pauses, R regenerates the sea, and Q quits.
"""

from __future__ import annotations

import argparse
import math
import time
from dataclasses import dataclass, fields

try:
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.animation import FuncAnimation
    from matplotlib.widgets import Button, CheckButtons, Slider
except ImportError as exc:
    raise SystemExit(
        "This simulator needs NumPy and Matplotlib.\n"
        "Install them with: python3 -m pip install -r requirements.txt"
    ) from exc


G_CONST = 6.67430e-11
EARTH_RADIUS = 6_371_000.0
MOON_MASS = 7.342e22
SUN_MASS = 1.98847e30
MOON_DISTANCE = 384_400_000.0
SUN_DISTANCE = 149_597_870_700.0
SIDEREAL_DAY = 86_164.0905
LUNAR_SEMIDIURNAL = 12.4206012 * 3600.0
SOLAR_SEMIDIURNAL = 12.0 * 3600.0
OMEGA_EARTH = 2.0 * math.pi / SIDEREAL_DAY
AIR_PRESSURE_STANDARD = 101_325.0


@dataclass
class OceanSettings:
    # Wind
    wind_speed: float = 12.0
    wind_direction: float = 35.0
    wind_duration: float = 6.0
    fetch: float = 50.0
    gustiness: float = 0.12
    directional_spread: float = 25.0
    # Earth
    gravity: float = 9.81
    earth_rotation: float = 1.0
    latitude: float = 24.86
    earth_radius_factor: float = 1.0
    # Moon and Sun
    moon_gravity: float = 1.0
    moon_distance: float = 1.0
    moon_phase: float = 0.5
    moon_declination: float = 5.1
    moon_orbit_position: float = 0.0
    sun_gravity: float = 1.0
    sun_distance: float = 1.0
    sun_position: float = 0.0
    # Water and seabed
    depth: float = 80.0
    temperature: float = 18.0
    salinity: float = 35.0
    surface_tension: float = 0.074
    viscosity_factor: float = 1.0
    damping: float = 1.0e-5
    seabed_slope: float = 0.0
    seabed_roughness: float = 0.15
    breaking_limit: float = 0.78
    coastal_reflection: float = 0.08
    # Swell and waves
    swell_height: float = 0.8
    swell_period: float = 11.0
    swell_direction: float = 210.0
    wave_steepness: float = 1.0
    # Current and weather
    current_speed: float = 0.35
    current_direction: float = 90.0
    current_shear: float = 0.0
    pressure: float = 1013.25
    storm_surge: float = 0.0
    rain_intensity: float = 0.0
    air_density: float = 1.225
    # Display and numerical controls
    time_scale: float = 1.0
    vertical_exaggeration: float = 1.8
    domain: float = 500.0
    grid: int = 62
    modes: int = 72
    seed: int = 7


# label, attribute, minimum, maximum, format
CONTROL_GROUPS = {
    "Wind": [
        ("Wind speed (m/s)", "wind_speed", 0.0, 40.0, "%1.1f"),
        ("Direction (°)", "wind_direction", 0.0, 360.0, "%1.0f"),
        ("Duration (hours)", "wind_duration", 0.1, 72.0, "%1.1f"),
        ("Fetch (km)", "fetch", 0.1, 800.0, "%1.1f"),
        ("Gustiness", "gustiness", 0.0, 0.6, "%1.2f"),
        ("Directional spread (°)", "directional_spread", 2.0, 80.0, "%1.0f"),
        ("Air density (kg/m³)", "air_density", 0.8, 1.5, "%1.3f"),
    ],
    "Earth": [
        ("Earth gravity (m/s²)", "gravity", 1.0, 20.0, "%1.2f"),
        ("Earth rotation (×)", "earth_rotation", 0.0, 3.0, "%1.2f"),
        ("Latitude (°)", "latitude", -90.0, 90.0, "%1.1f"),
        ("Earth radius (×)", "earth_radius_factor", 0.5, 2.0, "%1.2f"),
    ],
    "Moon & Sun": [
        ("Moon gravity (×)", "moon_gravity", 0.0, 3.0, "%1.2f"),
        ("Moon distance (×)", "moon_distance", 0.80, 1.20, "%1.3f"),
        ("Moon phase", "moon_phase", 0.0, 1.0, "%1.2f"),
        ("Moon declination (°)", "moon_declination", -28.6, 28.6, "%1.1f"),
        ("Moon orbit position (°)", "moon_orbit_position", 0.0, 360.0, "%1.0f"),
        ("Sun gravity (×)", "sun_gravity", 0.0, 3.0, "%1.2f"),
        ("Sun distance (×)", "sun_distance", 0.97, 1.03, "%1.3f"),
        ("Sun position (°)", "sun_position", 0.0, 360.0, "%1.0f"),
    ],
    "Water": [
        ("Water depth (m)", "depth", 1.0, 500.0, "%1.1f"),
        ("Temperature (°C)", "temperature", -2.0, 35.0, "%1.1f"),
        ("Salinity (PSU)", "salinity", 0.0, 42.0, "%1.1f"),
        ("Surface tension (N/m)", "surface_tension", 0.02, 0.10, "%1.3f"),
        ("Viscosity (×)", "viscosity_factor", 0.1, 10.0, "%1.2f"),
        ("Extra damping (1/s)", "damping", 0.0, 0.001, "%1.5f"),
        ("Seabed slope", "seabed_slope", -0.15, 0.15, "%1.3f"),
        ("Seabed roughness", "seabed_roughness", 0.0, 1.0, "%1.2f"),
        ("Breaking depth ratio", "breaking_limit", 0.3, 1.2, "%1.2f"),
        ("Coastal reflection", "coastal_reflection", 0.0, 0.8, "%1.2f"),
    ],
    "Waves": [
        ("Swell height (m)", "swell_height", 0.0, 10.0, "%1.2f"),
        ("Swell period (s)", "swell_period", 3.0, 25.0, "%1.1f"),
        ("Swell direction (°)", "swell_direction", 0.0, 360.0, "%1.0f"),
        ("Wave steepness (×)", "wave_steepness", 0.1, 2.0, "%1.2f"),
    ],
    "Current & Weather": [
        ("Current speed (m/s)", "current_speed", -3.0, 3.0, "%1.2f"),
        ("Current direction (°)", "current_direction", 0.0, 360.0, "%1.0f"),
        ("Current shear (1/s)", "current_shear", -0.01, 0.01, "%1.4f"),
        ("Air pressure (hPa)", "pressure", 900.0, 1060.0, "%1.1f"),
        ("Storm surge (m)", "storm_surge", -1.0, 8.0, "%1.2f"),
        ("Rain intensity (mm/h)", "rain_intensity", 0.0, 150.0, "%1.1f"),
    ],
    "Display": [
        ("Simulation speed (×)", "time_scale", 0.05, 500.0, "%1.2f"),
        ("Vertical exaggeration", "vertical_exaggeration", 0.2, 8.0, "%1.2f"),
    ],
}

REBUILD_FACTORS = {
    "wind_speed", "wind_direction", "wind_duration", "fetch", "gustiness",
    "directional_spread", "air_density", "gravity", "depth", "temperature",
    "salinity", "surface_tension", "seabed_slope", "seabed_roughness",
    "breaking_limit", "coastal_reflection", "swell_height", "swell_period",
    "swell_direction", "wave_steepness",
}


def water_density(temperature: float, salinity: float) -> float:
    """Compact seawater density approximation, adequate for visualization."""
    pure = 999.842594 + 6.793952e-2 * temperature - 9.09529e-3 * temperature**2
    return pure + 0.78 * salinity


class OceanModel:
    def __init__(self, settings: OceanSettings):
        self.s = settings
        self.elapsed = 0.0
        self.generation = 0
        self.rebuild()

    def rebuild(self, new_seed: bool = False) -> None:
        s = self.s
        if new_seed:
            s.seed += 1
        self.generation += 1
        rng = np.random.default_rng(s.seed)
        axis = np.linspace(-s.domain / 2.0, s.domain / 2.0, s.grid)
        self.x, self.y = np.meshgrid(axis, axis)
        rho = water_density(s.temperature, s.salinity)

        wind = max(s.wind_speed, 0.15)
        fetch_m = max(s.fetch * 1000.0, 1.0)
        duration_s = max(s.wind_duration * 3600.0, 1.0)
        tp_fetch = 7.54 * wind / s.gravity * (s.gravity * fetch_m / wind**2) ** (1.0 / 3.0)
        tp_duration = 0.72 * duration_s ** (1.0 / 3.0) * wind ** (1.0 / 3.0)
        pm_limit = 0.83 * 2.0 * math.pi * wind / s.gravity
        self.peak_period = float(np.clip(min(tp_fetch, tp_duration, pm_limit), 1.0, 22.0))
        peak_omega = 2.0 * math.pi / self.peak_period

        kp = peak_omega**2 / s.gravity
        for _ in range(12):
            local_depth = max(s.depth, 0.1)
            omega2 = (s.gravity * kp + s.surface_tension * kp**3 / rho) * math.tanh(kp * local_depth)
            kp *= float(np.clip(peak_omega / math.sqrt(max(omega2, 1e-12)), 0.5, 2.0))

        self.k = np.clip(
            np.exp(rng.normal(np.log(max(kp, 1e-5)), 0.74, s.modes)),
            2.0 * math.pi / (s.domain * 2.0),
            3.0,
        )
        direction = math.radians(s.wind_direction)
        spread = math.radians(max(s.directional_spread, 1.0))
        theta = direction + rng.normal(0.0, spread, s.modes)
        self.kx = self.k * np.cos(theta)
        self.ky = self.k * np.sin(theta)

        self.intrinsic_omega = np.sqrt(
            (s.gravity * self.k + s.surface_tension * self.k**3 / rho)
            * np.tanh(self.k * s.depth)
        )
        sigma = np.where(self.intrinsic_omega <= peak_omega, 0.07, 0.09)
        gamma = 3.3 ** np.exp(
            -((self.intrinsic_omega - peak_omega) ** 2)
            / (2.0 * sigma**2 * peak_omega**2)
        )
        density = (
            np.maximum(self.intrinsic_omega, 1e-4) ** -5
            * np.exp(-1.25 * (peak_omega / np.maximum(self.intrinsic_omega, 1e-4)) ** 4)
            * gamma
        )
        density /= max(float(density.sum()), 1e-12)

        hs_full = 0.21 * wind**2 / s.gravity
        fetch_growth = math.tanh(0.0125 * (s.gravity * fetch_m / wind**2) ** 0.42)
        duration_growth = math.tanh(duration_s / max(2500.0 * wind / s.gravity, 1.0))
        density_factor = math.sqrt(max(s.air_density, 0.1) / 1.225)
        gust_factor = 1.0 + 0.8 * s.gustiness
        self.significant_height = float(
            np.clip(hs_full * min(fetch_growth, duration_growth) * density_factor * gust_factor, 0.01, 18.0)
        )
        target_variance = (self.significant_height / 4.0) ** 2
        self.amplitude = (
            np.sqrt(2.0 * target_variance * density) * s.wave_steepness
        )
        self.phase = rng.uniform(0.0, 2.0 * math.pi, s.modes)
        self.gust_phase = rng.uniform(0.0, 2.0 * math.pi, s.modes)

        # Independent long-period swell components.
        swell_count = 8
        swell_theta = math.radians(s.swell_direction) + rng.normal(0.0, math.radians(4.0), swell_count)
        swell_omega = 2.0 * math.pi / max(s.swell_period, 0.2)
        swell_k = swell_omega**2 / s.gravity
        for _ in range(10):
            value = s.gravity * swell_k * math.tanh(swell_k * s.depth)
            swell_k *= float(np.clip(swell_omega / math.sqrt(max(value, 1e-12)), 0.5, 2.0))
        self.swell_kx = swell_k * np.cos(swell_theta)
        self.swell_ky = swell_k * np.sin(swell_theta)
        self.swell_omega = swell_omega
        self.swell_phase = rng.uniform(0.0, 2.0 * math.pi, swell_count)
        self.swell_amp = s.swell_height / max(2.0 * math.sqrt(swell_count), 1.0)

    def current(self, t: float) -> tuple[float, float]:
        s = self.s
        coriolis = (
            2.0 * OMEGA_EARTH * s.earth_rotation
            * math.sin(math.radians(s.latitude))
        )
        angle = math.radians(s.current_direction) + coriolis * t
        return s.current_speed * math.cos(angle), s.current_speed * math.sin(angle)

    def tide(self, t: float) -> tuple[float, float, float]:
        s = self.s
        radius = EARTH_RADIUS * s.earth_radius_factor
        moon_r = MOON_DISTANCE * max(s.moon_distance, 0.1)
        sun_r = SUN_DISTANCE * max(s.sun_distance, 0.1)
        declination_factor = 0.5 + 0.5 * math.cos(math.radians(s.moon_declination))
        moon_amp = (
            s.moon_gravity * G_CONST * MOON_MASS * radius**2
            / (s.gravity * moon_r**3) * declination_factor
        )
        sun_amp = (
            s.sun_gravity * G_CONST * SUN_MASS * radius**2
            / (s.gravity * sun_r**3)
        )
        moon_phase = (
            4.0 * math.pi * s.moon_phase
            + math.radians(2.0 * s.moon_orbit_position)
        )
        sun_phase = math.radians(2.0 * s.sun_position)
        moon = moon_amp * math.cos(2.0 * math.pi * t / LUNAR_SEMIDIURNAL + moon_phase)
        sun = sun_amp * math.cos(2.0 * math.pi * t / SOLAR_SEMIDIURNAL + sun_phase)
        return moon + sun, moon, sun

    def surface(self, t: float) -> np.ndarray:
        s = self.s
        u, v = self.current(t)
        viscosity = 1.05e-6 * max(s.viscosity_factor, 0.0)
        total_decay = (
            2.0 * viscosity * self.k**2
            + max(s.damping, 0.0)
            + s.seabed_roughness * 2e-6 / max(s.depth, 0.1)
            + s.rain_intensity * 2e-8
        )
        decay = np.exp(-total_decay * t)
        z = np.zeros_like(self.x)
        gust = 1.0 + s.gustiness * np.sin(0.17 * t + self.gust_phase)

        # Current shear changes phase speed across the north-south axis.
        shear_velocity = s.current_shear * self.y
        for amp, kx, ky, omega, phase, attenuation, gust_factor in zip(
            self.amplitude, self.kx, self.ky, self.intrinsic_omega,
            self.phase, decay, gust, strict=True,
        ):
            phase_field = (
                kx * self.x + ky * self.y
                - (omega + kx * u + ky * v) * t
                - kx * shear_velocity * t
                + phase
            )
            z += amp * attenuation * gust_factor * np.cos(phase_field)

        for kx, ky, phase in zip(
            self.swell_kx, self.swell_ky, self.swell_phase, strict=True
        ):
            z += self.swell_amp * np.cos(
                kx * self.x + ky * self.y
                - (self.swell_omega + kx * u + ky * v) * t + phase
            )

        # Simple reflected component from a notional coast at the left edge.
        if s.coastal_reflection > 0:
            z += s.coastal_reflection * np.flip(z, axis=1)

        # Depth changes across x for a sloping seabed. Shoaling grows amplitude;
        # a breaker-index limit caps physically implausible shallow-water waves.
        local_depth = np.maximum(
            0.25,
            s.depth + s.seabed_slope * self.x,
        )
        shoaling = np.clip(np.sqrt(s.depth / local_depth), 0.4, 2.5)
        breaker_height = np.maximum(s.breaking_limit * local_depth, 0.05)
        z = np.clip(z * shoaling, -breaker_height / 2.0, breaker_height / 2.0)

        rho = water_density(s.temperature, s.salinity)
        inverse_barometer = -(s.pressure * 100.0 - AIR_PRESSURE_STANDARD) / (rho * s.gravity)
        tide_total, _, _ = self.tide(t)
        return z + tide_total + inverse_barometer + s.storm_surge


class OceanApp:
    def __init__(self, settings: OceanSettings):
        self.s = settings
        self.model = OceanModel(settings)
        self.paused = False
        self.wireframe = False
        self.last_clock = time.perf_counter()
        self.last_draw = 0.0
        self.surface_artist = None
        self.slider_axes = []
        self.sliders = []
        self.category_buttons = []
        self.active_group = "Wind"

        self.fig = plt.figure(figsize=(15.5, 9.2), facecolor="#07111d")
        try:
            self.fig.canvas.manager.set_window_title("3D Ocean Physics Simulator")
        except AttributeError:
            pass
        self.ax = self.fig.add_axes([0.03, 0.16, 0.67, 0.79], projection="3d")
        self.ax.set_facecolor("#07111d")
        self.ax.view_init(elev=27, azim=-58)
        self.ax.set_xlabel("east–west (m)", color="white")
        self.ax.set_ylabel("north–south (m)", color="white")
        self.ax.set_zlabel("elevation (m)", color="white")
        self.ax.tick_params(colors="#b7cfdf")
        self.info = self.fig.text(
            0.04, 0.035, "", color="#d7efff", fontsize=10, family="monospace"
        )
        self.group_title = self.fig.text(
            0.735, 0.925, "", color="white", fontsize=14, weight="bold"
        )
        self._build_category_buttons()
        self._show_group("Wind")
        self._build_action_controls()
        self.fig.canvas.mpl_connect("key_press_event", self._on_key)

        self.animation = FuncAnimation(
            self.fig, self._animate, interval=65, blit=False, cache_frame_data=False
        )

    def _build_category_buttons(self) -> None:
        names = list(CONTROL_GROUPS)
        left, width, gap = 0.035, 0.088, 0.008
        for index, name in enumerate(names):
            ax_button = self.fig.add_axes([left + index * (width + gap), 0.105, width, 0.035])
            button = Button(ax_button, name, color="#19334a", hovercolor="#2b5778")
            button.label.set_color("white")
            button.label.set_fontsize(8.5)
            button.on_clicked(lambda _event, group=name: self._show_group(group))
            self.category_buttons.append((ax_button, button))

    def _build_action_controls(self) -> None:
        reset_ax = self.fig.add_axes([0.74, 0.055, 0.10, 0.038])
        self.reset_button = Button(reset_ax, "New sea (R)", color="#1e5870", hovercolor="#2b7999")
        self.reset_button.label.set_color("white")
        self.reset_button.on_clicked(lambda _event: self._regenerate())

        pause_ax = self.fig.add_axes([0.85, 0.055, 0.10, 0.038])
        self.pause_button = Button(pause_ax, "Pause", color="#1e5870", hovercolor="#2b7999")
        self.pause_button.label.set_color("white")
        self.pause_button.on_clicked(lambda _event: self._toggle_pause())

        check_ax = self.fig.add_axes([0.74, 0.012, 0.21, 0.032], facecolor="#07111d")
        self.check = CheckButtons(check_ax, ["Wireframe"], [False])
        for label in self.check.labels:
            label.set_color("white")
        self.check.on_clicked(lambda _label: self._toggle_wireframe())

    def _show_group(self, group: str) -> None:
        for slider_ax in self.slider_axes:
            slider_ax.remove()
        self.slider_axes.clear()
        self.sliders.clear()
        self.active_group = group
        self.group_title.set_text(group)
        specs = CONTROL_GROUPS[group]
        top, bottom = 0.865, 0.17
        spacing = min(0.084, (top - bottom) / max(len(specs), 1))
        for index, (label, attr, minimum, maximum, fmt) in enumerate(specs):
            y = top - index * spacing
            ax_slider = self.fig.add_axes([0.75, y, 0.20, 0.026], facecolor="#18334a")
            slider = Slider(
                ax_slider, label, minimum, maximum,
                valinit=float(getattr(self.s, attr)), valfmt=fmt,
                color="#2ba8d8",
            )
            slider.label.set_color("#d7efff")
            slider.valtext.set_color("white")
            slider.on_changed(lambda value, name=attr: self._factor_changed(name, value))
            self.slider_axes.append(ax_slider)
            self.sliders.append(slider)
        self.fig.canvas.draw_idle()

    def _factor_changed(self, name: str, value: float) -> None:
        setattr(self.s, name, float(value))
        if name in REBUILD_FACTORS:
            self.model.rebuild()

    def _regenerate(self) -> None:
        self.model.rebuild(new_seed=True)

    def _toggle_pause(self) -> None:
        self.paused = not self.paused
        self.pause_button.label.set_text("Resume" if self.paused else "Pause")
        self.last_clock = time.perf_counter()

    def _toggle_wireframe(self) -> None:
        self.wireframe = not self.wireframe

    def _on_key(self, event) -> None:
        key = (event.key or "").lower()
        if key == " ":
            self._toggle_pause()
        elif key == "r":
            self._regenerate()
        elif key in {"q", "escape"}:
            plt.close(self.fig)

    def _animate(self, _frame):
        now = time.perf_counter()
        dt = min(now - self.last_clock, 0.15)
        self.last_clock = now
        if not self.paused:
            self.model.elapsed += dt * self.s.time_scale

        # Keep interactive 3D plotting responsive on typical laptops.
        if now - self.last_draw < 0.06:
            return ()
        self.last_draw = now
        z = self.model.surface(self.model.elapsed)
        exaggeration = self.s.vertical_exaggeration
        display_z = z * exaggeration
        if self.surface_artist is not None:
            self.surface_artist.remove()
        if self.wireframe:
            self.surface_artist = self.ax.plot_wireframe(
                self.model.x, self.model.y, display_z,
                rstride=2, cstride=2, color="#4cc9f0", linewidth=0.42,
            )
        else:
            self.surface_artist = self.ax.plot_surface(
                self.model.x, self.model.y, display_z,
                cmap="ocean", rstride=1, cstride=1,
                linewidth=0, antialiased=True, shade=True,
            )
        limit = max(
            0.6,
            (self.model.significant_height + self.s.swell_height + abs(self.s.storm_surge))
            * 0.85 * exaggeration,
        )
        self.ax.set_zlim(-limit, limit)
        tide, moon, sun = self.model.tide(self.model.elapsed)
        rho = water_density(self.s.temperature, self.s.salinity)
        u, v = self.model.current(self.model.elapsed)
        self.ax.set_title(
            "Interactive 3D Ocean Surface",
            color="white", fontsize=16, pad=14,
        )
        self.info.set_text(
            f"time {self.model.elapsed:9.1f} s   Hs {self.model.significant_height:5.2f} m   "
            f"peak period {self.model.peak_period:5.2f} s   tide {tide:+6.3f} m\n"
            f"lunar {moon:+6.3f} m   solar {sun:+6.3f} m   density {rho:7.2f} kg/m³   "
            f"current ({u:+4.2f}, {v:+4.2f}) m/s"
        )
        return (self.surface_artist,)

    def show(self) -> None:
        plt.show()


def parse_args() -> OceanSettings:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wind-speed", type=float, default=12.0)
    parser.add_argument("--depth", type=float, default=80.0)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--grid", type=int, default=62)
    parser.add_argument("--modes", type=int, default=72)
    args = parser.parse_args()
    if args.depth <= 0 or args.grid < 20 or args.modes < 8:
        parser.error("depth must be positive, grid >= 20, and modes >= 8")
    return OceanSettings(
        wind_speed=max(args.wind_speed, 0.0),
        depth=args.depth,
        seed=args.seed,
        grid=args.grid,
        modes=args.modes,
    )


if __name__ == "__main__":
    OceanApp(parse_args()).show()
