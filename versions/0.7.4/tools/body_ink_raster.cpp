// Authoring tool only: sample the shipped, editable SVG costumes into compact
// horizontal outlines. The Scratch runtime needs no font or rendering library.
#include <QByteArray>
#include <QFile>
#include <QImage>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPainter>
#include <QSvgRenderer>
#include <algorithm>
#include <cmath>
#include <cstdio>

int main(int argc, char **argv) {
    if (argc != 3) return 1;
    QFile input(argv[1]);
    if (!input.open(QIODevice::ReadOnly)) return 2;
    QJsonObject bank;
    for (auto item : QJsonDocument::fromJson(input.readAll()).array()) {
        const auto c = item.toObject();
        QSvgRenderer svg(QByteArray::fromBase64(c["svg"].toString().toLatin1()));
        if (!svg.isValid()) return 3;
        const auto size = svg.defaultSize();
        constexpr int resolution = 8, width = 24, height = 22;
        QImage pixels(width*resolution,height*resolution,QImage::Format_ARGB32);
        pixels.fill(Qt::transparent);
        QPainter p(&pixels);
        p.scale(resolution,resolution);
        p.setRenderHint(QPainter::Antialiasing);
        svg.render(&p,QRectF(12-c["cx"].toDouble(),11-c["cy"].toDouble(),size.width(),size.height()));
        p.end();
        QJsonArray rows;
        // Each source row has half-pixel height. Each endpoint has quarter-pixel precision.
        for (int row=0;row<height*2;row++) {
            const int y=row*4+2;
            QString runs;
            int left=0,previous=0;
            for (int x=0;x<=width*4;x++) {
                int tone=0;
                if (x<width*4) {
                    QRgb rgb=pixels.pixel(x*2+1,y);
                    if(qAlpha(rgb)>83) tone=qRed(rgb)>144 ? 2 : 1;
                }
                if (tone!=previous) {
                    if(previous)runs+=QString::number(previous)+QString("%1%2")
                        .arg(left,2,10,QChar('0')).arg(x,2,10,QChar('0'));
                    left=x;previous=tone;
                }
            }
            rows.append(runs);
        }
        bank[c["hash"].toString()] = rows;
    }
    QFile output(argv[2]);
    if (!output.open(QIODevice::WriteOnly)) return 4;
    output.write(QJsonDocument(bank).toJson(QJsonDocument::Compact));return 0;
}
