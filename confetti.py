# mypy: disable-error-code="import-untyped,misc"
from __future__ import annotations

import logging
import os
from typing import Any

import objc
from Foundation import NSObject, NSTimer

logger = logging.getLogger(__name__)

_ACTIVE_WINDOWS: list[Any] = []
_ACTIVE_CLOSERS: list[Any] = []
_ConfettiWindow: Any = None


class _ConfettiCloser(NSObject):
    target_window = objc.ivar()

    def initWithWindow_(self, target_window: Any) -> Any:
        self = objc.super(_ConfettiCloser, self).init()
        if self is None:
            return None
        self.target_window = target_window
        return self

    def closeWindow_(self, timer: Any) -> None:
        try:
            self.target_window.animator().setAlphaValue_(0.0)
            self.target_window.close()
        finally:
            if self.target_window in _ACTIVE_WINDOWS:
                _ACTIVE_WINDOWS.remove(self.target_window)
            if self in _ACTIVE_CLOSERS:
                _ACTIVE_CLOSERS.remove(self)


def celebrate(duration: float = 5.0) -> None:
    try:
        _celebrate_with_emitter(duration)
    except Exception:
        if os.environ.get("USAGE_DEBUG") == "1":
            logger.warning("confetti emitter failed", exc_info=True)
        try:
            _celebrate_with_text(min(duration, 3.0))
        except Exception:
            if os.environ.get("USAGE_DEBUG") == "1":
                logger.warning("confetti fallback failed", exc_info=True)


def _celebrate_with_emitter(duration: float) -> None:
    from AppKit import (
        NSApp,
        NSBackingStoreBuffered,
        NSColor,
        NSFloatingWindowLevel,
        NSScreen,
        NSView,
        NSWindowCollectionBehaviorCanJoinAllSpaces,
        NSWindowCollectionBehaviorStationary,
        NSWindowStyleMaskBorderless,
    )
    from Quartz import CAEmitterCell, CAEmitterLayer

    if NSApp() is None:
        return
    screen = NSScreen.mainScreen()
    if screen is None:
        return
    frame = screen.frame()
    window = _ConfettiWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame,
        NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered,
        False,
    )
    window.setOpaque_(False)
    window.setBackgroundColor_(NSColor.clearColor())
    window.setIgnoresMouseEvents_(True)
    window.setLevel_(NSFloatingWindowLevel + 1)
    window.setCollectionBehavior_(
        NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorStationary
    )
    window.setReleasedWhenClosed_(False)

    view = NSView.alloc().initWithFrame_(frame)
    view.setWantsLayer_(True)
    emitter = CAEmitterLayer.layer()
    emitter.setEmitterPosition_((frame.size.width / 2.0, frame.size.height + 20.0))
    emitter.setEmitterSize_((frame.size.width, 1.0))
    emitter.setEmitterShape_("line")
    emitter.setBirthRate_(1.0)

    # CGImageForProposedRect... returns a (CGImage, CGRect) tuple in PyObjC; the
    # cell contents needs the CGImage element, not the whole tuple.
    confetti_cg = _confetti_image().CGImageForProposedRect_context_hints_(None, None, None)[0]
    cells = []
    colors = [
        NSColor.systemPinkColor().CGColor(),
        NSColor.systemYellowColor().CGColor(),
        NSColor.systemTealColor().CGColor(),
        NSColor.systemGreenColor().CGColor(),
        NSColor.systemOrangeColor().CGColor(),
    ]
    for index, color in enumerate(colors):
        cell = CAEmitterCell.emitterCell()
        cell.setName_(f"confetti-{index}")
        cell.setBirthRate_(28.0)
        cell.setLifetime_(duration + 2.0)
        cell.setVelocity_(220.0)
        cell.setVelocityRange_(120.0)
        cell.setYAcceleration_(-160.0)
        cell.setXAcceleration_(0.0)
        cell.setEmissionLongitude_(3.14159)
        cell.setEmissionRange_(0.9)
        cell.setSpin_(3.0)
        cell.setSpinRange_(5.0)
        cell.setScale_(1.0)
        cell.setScaleRange_(0.5)
        cell.setColor_(color)
        cell.setContents_(confetti_cg)
        cells.append(cell)
    emitter.setEmitterCells_(cells)
    view.layer().addSublayer_(emitter)
    window.setContentView_(view)
    window.orderFrontRegardless()
    _ACTIVE_WINDOWS.append(window)
    _schedule_close(window, duration)


def _celebrate_with_text(duration: float) -> None:
    from AppKit import (
        NSApp,
        NSBackingStoreBuffered,
        NSColor,
        NSFloatingWindowLevel,
        NSFont,
        NSMakeRect,
        NSScreen,
        NSTextField,
        NSWindowCollectionBehaviorCanJoinAllSpaces,
        NSWindowCollectionBehaviorStationary,
        NSWindowStyleMaskBorderless,
    )

    if NSApp() is None:
        return
    screen = NSScreen.mainScreen()
    if screen is None:
        return
    frame = screen.frame()
    window = _ConfettiWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame,
        NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered,
        False,
    )
    window.setOpaque_(False)
    window.setBackgroundColor_(NSColor.clearColor())
    window.setIgnoresMouseEvents_(True)
    window.setLevel_(NSFloatingWindowLevel + 1)
    window.setCollectionBehavior_(
        NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorStationary
    )
    window.setReleasedWhenClosed_(False)
    label_frame = NSMakeRect(
        (frame.size.width - 500.0) / 2.0,
        (frame.size.height - 120.0) / 2.0,
        500.0,
        120.0,
    )
    label = NSTextField.alloc().initWithFrame_(label_frame)
    label.setStringValue_("🎉")
    label.setFont_(NSFont.systemFontOfSize_(72.0))
    label.setTextColor_(NSColor.labelColor())
    label.setBackgroundColor_(NSColor.clearColor())
    label.setBordered_(False)
    label.setEditable_(False)
    label.setSelectable_(False)
    label.setAlignment_(1)
    window.setContentView_(label)
    window.orderFrontRegardless()
    _ACTIVE_WINDOWS.append(window)
    _schedule_close(window, duration)


def _confetti_image() -> Any:
    from AppKit import NSBezierPath, NSColor, NSImage, NSMakeRect, NSSize

    image = NSImage.alloc().initWithSize_(NSSize(24.0, 14.0))
    image.lockFocus()
    NSColor.whiteColor().set()
    NSBezierPath.bezierPathWithRect_(NSMakeRect(0.0, 0.0, 24.0, 14.0)).fill()
    image.unlockFocus()
    return image


def _schedule_close(window: Any, duration: float) -> None:
    closer = _ConfettiCloser.alloc().initWithWindow_(window)
    _ACTIVE_CLOSERS.append(closer)
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        max(0.1, duration),
        closer,
        "closeWindow:",
        None,
        False,
    )


def _make_window_class() -> None:
    from AppKit import NSWindow

    global _ConfettiWindow

    class ConfettiWindow(NSWindow):
        def canBecomeKeyWindow(self) -> bool:
            return False

        def canBecomeMainWindow(self) -> bool:
            return False

    _ConfettiWindow = ConfettiWindow


try:
    _make_window_class()
except Exception:
    if os.environ.get("USAGE_DEBUG") == "1":
        logger.warning("confetti window class setup failed", exc_info=True)
