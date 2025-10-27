from flask import Flask, request, jsonify
import requests
import re
import json

app = Flask(__name__)

class GuncelAdresSorgu:
    def __init__(self):
        self.api_url = "https://api.kahin.org/kahinapi/guncel-adres"
    
    def tc_dogrula(self, tc):
        if len(tc) != 11 or tc[0] == '0' or not tc.isdigit():
            return False
        
        tek = sum(int(tc[i]) for i in range(0, 9, 2))
        cift = sum(int(tc[i]) for i in range(1, 9, 2))
        
        toplam10 = (tek * 7 - cift) % 10
        toplam11 = (tek + cift + toplam10) % 10
        
        return toplam10 == int(tc[9]) and toplam11 == int(tc[10])
    
    def api_istek(self, tc):
        try:
            url = f"{self.api_url}?tc={tc}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"API hatası: {str(e)}"}
        except json.JSONDecodeError:
            return {"error": "Geçersiz JSON yanıtı"}
    
    def reklamlari_temizle(self, metin):
        if not isinstance(metin, str):
            return metin
            
        reklamlar = [
            r'kahin', r'sahibinden', 
            r'n[\.\s]*a[\.\s]*b[\.\s]*i[\.\s]*s[\.\s]*y[\.\s]*s[\.\s]*t[\.\s]*e[\.\s]*m',
            r'telegram', r'https?://[^\s]+', r'@[^\s]+'
        ]
        
        for reklam in reklamlar:
            metin = re.sub(reklam, '', metin, flags=re.IGNORECASE)
        
        return metin.strip()
    
    def adres_birlestir(self, veri):
        adres = ""
        if veri.get('mahalle'):
            adres += f"{veri['mahalle']} Mah. "
        if veri.get('cadde'):
            adres += f"{veri['cadde']} Cad. "
        if veri.get('sokak'):
            adres += f"{veri['sokak']} Sok. "
        if veri.get('binaNo'):
            adres += f"No:{veri['binaNo']} "
        if veri.get('daireNo'):
            adres += f"D:{veri['daireNo']} "
        if veri.get('ilce'):
            adres += f"{veri['ilce']}/"
        if veri.get('il'):
            adres += f"{veri['il']}"
        
        return adres.strip()
    
    def veriyi_temizle(self, data):
        temiz_veri = {"status": "success"}
        alanlar = ['adres', 'il', 'ilce', 'mahalle', 'cadde', 'sokak', 'binaNo', 'daireNo', 'postaKodu']
        
        for alan in alanlar:
            if data.get(alan):
                temiz_veri[alan] = self.reklamlari_temizle(data[alan])
        
        if not temiz_veri.get('adres') and temiz_veri.get('il'):
            temiz_veri['adres'] = self.adres_birlestir(temiz_veri)
        
        return temiz_veri
    
    def sorgula(self, tc):
        if not self.tc_dogrula(tc):
            return {"error": "Geçersiz TC kimlik numarası", "code": 400}
        
        response = self.api_istek(tc)
        
        if response.get('error'):
            return response
        
        return self.veriyi_temizle(response)

# Flask Routes
adres_sorgu = GuncelAdresSorgu()

@app.route('/')
def ana_sayfa():
    return jsonify({
        "api": "Güncel Adres Sorgu API",
        "version": "1.0",
        "teknoloji": "Python Flask",
        "endpoints": {
            "adres_sorgu": "/api/sorgu?tc=TCKIMLIKNO"
        },
        "examples": [
            "/api/sorgu?tc=11111111111"
        ]
    })

@app.route('/api/sorgu')
def api_sorgu():
    tc = request.args.get('tc')
    
    if not tc:
        return jsonify({
            "error": "TC kimlik parametresi gerekli",
            "usage": "/api/sorgu?tc=11111111111"
        }), 400
    
    sonuc = adres_sorgu.sorgula(tc)
    
    status_code = sonuc.get('code', 200)
    if 'code' in sonuc:
        del sonuc['code']
    
    return jsonify(sonuc), status_code

@app.route('/api/sorgu/<tc>')
def api_sorgu_direct(tc):
    sonuc = adres_sorgu.sorgula(tc)
    
    status_code = sonuc.get('code', 200)
    if 'code' in sonuc:
        del sonuc['code']
    
    return jsonify(sonuc), status_code

# Health check
@app.route('/health')
def health_check():
    return jsonify({"status": "OK", "service": "Adres API"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
