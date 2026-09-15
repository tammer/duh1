//
//  FloatingPanel.swift
//  Duh
//

import AppKit
import SwiftUI

final class FloatingPanelController {
    private let panel: NSPanel
    private let model: HudModel

    init(model: HudModel) {
        self.model = model
        let content = HudRootView(model: model)
        let hosting = NSHostingController(rootView: content)

        let panel = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: 360, height: 420),
            styleMask: [.titled, .closable, .resizable, .nonactivatingPanel, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        panel.title = "Duh"
        panel.titleVisibility = .visible
        panel.isFloatingPanel = true
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.hidesOnDeactivate = false
        panel.isReleasedWhenClosed = false
        panel.becomesKeyOnlyIfNeeded = true
        panel.contentViewController = hosting
        panel.minSize = NSSize(width: 300, height: 280)

        if let screen = NSScreen.main {
            let frame = screen.visibleFrame
            let origin = NSPoint(
                x: frame.maxX - panel.frame.width - 24,
                y: frame.maxY - panel.frame.height - 24
            )
            panel.setFrameOrigin(origin)
        }

        self.panel = panel
    }

    func show() {
        panel.orderFrontRegardless()
    }
}
