import Foundation
import Vision
import ImageIO

// Local-only OCR. Normalized boxes use a bottom-left origin.
let url = URL(fileURLWithPath: CommandLine.arguments[1])
let request = VNRecognizeTextRequest()
request.usesCPUOnly = true
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
request.recognitionLanguages = ["en-US"]
do {
    try VNImageRequestHandler(url: url).perform([request])
} catch {
    FileHandle.standardError.write(Data("Local OCR failed: \(error)\n".utf8))
    exit(2)
}
let items = (request.results ?? []).compactMap { observation -> [String: Any]? in
    guard let candidate = observation.topCandidates(1).first else { return nil }
    let box = observation.boundingBox
    return ["text": candidate.string, "confidence": candidate.confidence,
            "x": box.minX, "y": box.minY, "w": box.width, "h": box.height]
}
let output: [String: Any] = ["engine": "apple-vision", "revision": request.revision,
    "os": ProcessInfo.processInfo.operatingSystemVersionString, "items": items]
FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject: output, options: [.sortedKeys]))
