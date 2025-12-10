

        right_box = QVBoxLayout()



        self.preview_scene = QGraphicsScene(self)

        self.preview_view = QGraphicsView(self.preview_scene)

        self.preview_view.setRenderHints(

            self.preview_view.renderHints()

            | QPainter.Antialiasing

            | QPainter.TextAntialiasing

        )

        right_box.addWidget(self.preview_view, 3)



        self.layers_group = QGroupBox("Layers επιλεγμένου πολυγώνου")

        self.layers_layout = QVBoxLayout(self.layers_group)

        self.layers_layout.setContentsMargins(6,6,6,6)

        self.layers_layout.setSpacing(3)

        right_box.addWidget(self.layers_group, 2)



        main.addLayout(right_box, 2)



        btns = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)

        btns.accepted.connect(self.accept)

        btns.rejected.connect(self.reject)

        main.addWidget(btns)



        self._layer_checks: Dict[str,QCheckBox] = {}

        if self.items:

            self.list.setCurrentRow(0)



    def _role_key(self, r:str)->str:

        if r=="final":

            return "final_out"

        return r



    def on_poly_changed(self, row:int):

        self.preview_scene.clear()

        for i in reversed(range(self.layers_layout.count())):

            w = self.layers_layout.itemAt(i).widget()

            if w:

                w.deleteLater()

        self._layer_checks.clear()

        if row<0 or row>=len(self.items):

            return

        it = self.items[row]



        poly = it.polygon

        if not poly.is_empty:

            coords = list(poly.exterior.coords)

            if len(coords)>=2:

                path = QPainterPath(QPointF(coords[0][0], -coords[0][1]))

                for x,y in coords[1:]:

                    path.lineTo(QPointF(x,-y))

                item = QGraphicsPathItem(path)

                item.setPen(QPen(Qt.black, 0))

                self.preview_scene.addItem(item)

                rect = self.preview_scene.itemsBoundingRect()

                self.preview_view.setSceneRect(rect)

                self.preview_view.fitInView(rect, Qt.KeepAspectRatio)



        curr_layers = set(self.layers_by_poly.get(id(it), []))

        mandatory = set(MANDATORY_LAYERS_BY_ROLE.get(it.role, []))



        info = QLabel(

            f"Πολύγωνο: {it.name}  (ρόλος: {it.role})\n"

            f"Υποχρεωτικά layers: {', '.join(mandatory) if mandatory else '—'}"

        )

        self.layers_layout.addWidget(info)



        for ln in PRIMARY_LAYERS:

            chk = QCheckBox(ln)

            chk.setChecked(ln in curr_layers)

            if ln in mandatory:

                chk.setStyleSheet("color: red; font-weight: 600;")

            def handler(state, layer_name=ln, item=it, mandatory_set=mandatory, chk_ref=chk):

                ls = self.layers_by_poly.setdefault(id(item), [])

                if state == Qt.Checked:

                    if layer_name not in ls:

                        ls.append(layer_name)

                else:

                    if layer_name in mandatory_set:

                        QMessageBox.warning(

                            self,

                            "Υποχρεωτικό layer",

                            f"Το layer «{layer_name}» είναι ΥΠΟΧΡΕΩΤΙΚΟ για το πολύγωνο {item.name}."

                        )

                        chk_ref.blockSignals(True)

                        chk_ref.setChecked(True)

                        chk_ref.blockSignals(False)

                        return

                    if layer_name in ls:

                        ls.remove(layer_name)

            chk.stateChanged.connect(handler)

            self.layers_layout.addWidget(chk)

            self._layer_checks[ln] = chk



        self.layers_layout.addStretch(1)



    def accept(self):

        for it in self.items:

            ls = self.layers_by_poly.get(id(it), [])

            if not ls:

                base = list(DEFAULT_ROLE_LAYERS_MULTI.get(self._role_key(it.role), []))

                it.layers = base

            else:

                it.layers = list(ls)

        super().accept()



# ===================== Tables (GUI) =====================

@dataclass

class TableRow:

    name:str

    area:float

    perim:float

    verts:str

    dists:str



def rows_for_polys(items:List[PolyItem], id_to_point:List[Tuple[float,float]]):

    out=[]

    for p in items:

        pairs=edge_pairs_list(p.point_ids,id_to_point,2) if (p.point_ids and id_to_point) else []

        dists="\n".join(group_pairs_fixed(pairs,4)) if pairs else ""

        out.append(TableRow(

            p.name,

            float(p.polygon.area),

            float(p.polygon.length),

            format_vertices_cycle(p.point_ids),

            dists

        ))

    return out



def equalize_table_lengths(groups:Dict[str,List[TableRow]]):

    n=max((len(v) for v in groups.values()), default=0)

    for lst in groups.values():

        while len(lst)<n:

            lst.append(TableRow("",0.0,0.0,"",""))



# ===================== Scene items =====================

class PolyNameLabelItem(QGraphicsTextItem):

    def __init__(self, text: str, poly_item: PolyItem, on_rename_cb):

        super().__init__(text)

        self.poly_item = poly_item

        self.on_rename_cb = on_rename_cb

        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)

        f = QFont("Arial"); f.setPixelSize(GUI_LABEL_FONT_PX)

        self.setFont(f)

        self.setDefaultTextColor(QColor(40,40,40))

        self.setZValue(1000)

        self.setTextInteractionFlags(Qt.NoTextInteraction)

    def mouseDoubleClickEvent(self, e):

        self.setTextInteractionFlags(Qt.TextEditorInteraction)

        self.setFocus(Qt.MouseFocusReason)

        super().mouseDoubleClickEvent(e)

    def focusOutEvent(self, e):

        super().focusOutEvent(e)

        self.setTextInteractionFlags(Qt.NoTextInteraction)

        new = self.toPlainText().strip()

        if new and new != self.poly_item.name:

            self.poly_item.name = new

            if callable(self.on_rename_cb):

                self.on_rename_cb()



class VertexMarkerItem(QGraphicsItem):

    def __init__(self, x, y, text: str,

                 px_radius=GUI_VERTEX_PX_RADIUS,

                 px_offset=GUI_VERTEX_PX_OFFSET,

                 font_px=GUI_VERTEX_FONT_PX):

        super().__init__()

        self.x = x; self.y = y; self.text = text

        self.px_radius = px_radius; self.px_offset = px_offset; self.font_px = font_px

        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)

        self.setZValue(1100)

    def boundingRect(self):

        r = self.px_radius + self.px_offset + self.font_px * 2

        return QRectF(self.x - r, -self.y - r, 2 * r, 2 * r)

    def paint(self, painter, option, widget=None):

        painter.setPen(QPen(QColor(255, 255, 255), 3))

        painter.setBrush(QBrush(QColor(0, 0, 0)))

        painter.drawEllipse(QPointF(self.x, -self.y), self.px_radius, self.px_radius)

        painter.setPen(QPen(QColor(0, 0, 0), 1))

        f = QFont("Arial"); f.setPixelSize(self.font_px)

        painter.setFont(f)

        painter.drawText(self.x + self.px_offset, -self.y - self.px_offset, self.text)



class ZoomableView(QGraphicsView):

    def __init__(self,scene):

        super().__init__(scene)

        self.setRenderHints(self.renderHints()|

                            QPainter.Antialiasing|

                            QPainter.TextAntialiasing|

                            QPainter.SmoothPixmapTransform)

        self.setDragMode(QGraphicsView.ScrollHandDrag)

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

    def wheelEvent(self,e):

        s=1.15 if e.angleDelta().y()>0 else 1/1.15

        self.scale(s,s)



# ===================== Settings dialog =====================

class SettingsDialog(QDialog):

    def __init__(self, parent, get_scale, set_scale, get_grid, set_grid, get_text_h, set_text_h, extras):

        super().__init__(parent)

        self.setWindowTitle("Ρυθμίσεις")

        self.resize(420, 320)

        self._set_scale=set_scale; self._set_grid=set_grid; self._set_text_h=set_text_h

        lay=QVBoxLayout(self)



        form=QFormLayout()

        self.cmb_scale=QComboBox(); self.cmb_scale.setEditable(True)

        self.cmb_scale.addItems([f"1:{n}" for n in SCALE_OPTIONS])

        self.cmb_scale.setCurrentText(f"1:{get_scale()}")

        self.spn_grid=QDoubleSpinBox(); self.spn_grid.setDecimals(2)

        self.spn_grid.setRange(0.01,100000.0); self.spn_grid.setValue(get_grid())

        self.spn_text=QDoubleSpinBox(); self.spn_text.setRange(0.05,20.0)

        self.spn_text.setValue(max(DXF_TEXT_HEIGHT_MIN, get_text_h()))

        form.addRow("Κλίμακα", self.cmb_scale)

        form.addRow("Βήμα καννάβου (m)", self.spn_grid)

        form.addRow("Ύψος κειμένου DXF (m)", self.spn_text)

        lay.addLayout(form)



        self.cmb_scale.currentTextChanged.connect(self.on_scale_changed)



        gb=QGroupBox("Extras στο DXF")

        gbl=QGridLayout(gb)

        self.chk_title=QCheckBox("Τίτλος/Πλαίσιο"); self.chk_title.setChecked(extras["title"]())

        self.chk_north=QCheckBox("Βόρειο βέλος"); self.chk_north.setChecked(extras["north"]())

        self.chk_legend=QCheckBox("Legend"); self.chk_legend.setChecked(extras["legend"]())

        self.chk_meta=QCheckBox("Στοιχεία έργου"); self.chk_meta.setChecked(extras["meta"]())

        gbl.addWidget(self.chk_title,0,0); gbl.addWidget(self.chk_north,0,1)

        gbl.addWidget(self.chk_legend,1,0); gbl.addWidget(self.chk_meta,1,1)

        lay.addWidget(gb)



        btns=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)

        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)

        lay.addWidget(btns)



    def on_scale_changed(self, text:str):

        try:

            s = unicodedata.normalize("NFKC", text or "")

            nums = re.findall(r"(\d+)", s)

            den = int(nums[-1]) if nums else None

            if den and den in SCALE_GRID_DEFAULTS:

                self.spn_grid.setValue(SCALE_GRID_DEFAULTS[den])

        except Exception:

            pass



    def values(self):

        return {

            "scale": self.cmb_scale.currentText(),

            "grid": float(self.spn_grid.value()),

            "text_h": float(self.spn_text.value()),

            "title": self.chk_title.isChecked(),

            "north": self.chk_north.isChecked(),

            "legend": self.chk_legend.isChecked(),

            "meta": self.chk_meta.isChecked(),

        }



# ===================== Token / Signing helpers =====================

def compute_sha512_hash(file_path: str) -> str:

    sha512 = hashlib.sha512()

    with open(file_path, "rb") as f:

        for chunk in iter(lambda: f.read(8192), b""):

            sha512.update(chunk)

    return sha512.hexdigest()



def create_hash_only_pdf(hash_value: str, output_path: str):

    c = pdf_canvas.Canvas(output_path, pagesize=A4)

    c.setFont("Courier", 9)

    x = 20 * mm

    y = A4[1] - 30 * mm

    line_len = 100

    for i in range(0, len(hash_value), line_len):

        c.drawString(x, y, hash_value[i:i+line_len])

        y -= 5 * mm

        if y < 20 * mm:

            c.showPage()

            c.setFont("Courier", 9)

            y = A4[1] - 30 * mm

    c.save()



def _auto_find_pkcs11_lib() -> Optional[str]:

    candidates = [

        r"C:\Windows\System32\eTPKCS11.dll",

        r"C:\Windows\System32\acpkcs211.dll",

        r"C:\Windows\System32\dkck232.dll",

        r"C:\Program Files\SafeNet\Authentication\SAC\x64\eTPKCS11.dll",

        r"C:\Program Files\Gemalto\IDPrime\idprimepkcs11.dll",

        r"C:\Program Files\Gemalto\IDPrime\pkcs11.dll",

    ]

    for p in candidates:

        if os.path.exists(p):

            return p

    return None



def open_token_once(pin: str):

    if not SIGNING_OK:

        raise RuntimeError("Λείπουν τα πακέτα pkcs11 / endesive / cryptography.")

    lib_path = _auto_find_pkcs11_lib()

    if not lib_path:

        raise RuntimeError("Δεν βρέθηκε βιβλιοθήκη PKCS#11 (eTPKCS11.dll κλπ).")

    pkcs11 = pkcs11_lib(lib_path)

    slots = pkcs11.get_slots(token_present=True)

    if not slots:

        raise RuntimeError("Δεν βρέθηκε συνδεδεμένο USB token.")

    slot = slots[0]

    token = slot.get_token()

    session = token.open(user_pin=pin)



    certs = list(session.get_objects({Attribute.CLASS: ObjectClass.CERTIFICATE}))

    if not certs:

        session.close()

        raise RuntimeError("Δεν βρέθηκε πιστοποιητικό στο token.")

    cert_obj = certs[0]

    cert_der = bytes(cert_obj[Attribute.VALUE])



    try:

        cert = cryptox509.load_der_x509_certificate(cert_der, default_backend())

        cn_attr = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0]

        owner_name = cn_attr.value

    except Exception:

        owner_name = "Υπογράφων"



    priv_keys = list(

        session.get_objects({

            Attribute.CLASS: ObjectClass.PRIVATE_KEY,

            Attribute.KEY_TYPE: KeyType.RSA

        })

    )

    if not priv_keys:

        session.close()

        raise RuntimeError("Δεν βρέθηκε ιδιωτικό κλειδί RSA στο token.")

    privkey = priv_keys[0]



    return cert_der, privkey, session, owner_name



class TokenSigner:

    def __init__(self, privkey, cert_der):

        self.privkey = privkey

        self.cert_der = cert_der

    def sign(self, keyid, tosign, hashalgo):

        return self.privkey.sign(tosign, mechanism=Mechanism.SHA256_RSA_PKCS)

    def certificate(self):

        return None, self.cert_der



def sign_pdf_invisible(pdf_path: str, signed_path: str,

                       privkey, cert_der) -> None:

    with open(pdf_path, "rb") as f:

        original = f.read()

    hsm = TokenSigner(privkey, cert_der)

    now = datetime.datetime.utcnow()

    date_str = now.strftime("D:%Y%m%d%H%M%S+00'00'").encode("ascii")

    dct = {

        "sigflags": 3,

        "sigandcertify": True,

        "signingdate": date_str,

        "reason": "Υποβολή στο Ελληνικό Κτηματολόγιο",

    }

    update = cms.sign(

        datau=original,

        udct=dct,

        key=None,

        cert=None,

        othercerts=[],

        algomd="sha256",

        hsm=hsm,

    )

    with open(signed_path, "wb") as f:

        f.write(original)

        f.write(update)



# ===================== Main Window =====================

class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("ΤΔ/ΔΓΜ — Compact iOS-CAD (Full)")

        self.resize(1280, 720)



        self.layer_manager=LayerManager()

        self.items_initial:List[PolyItem]=[]

        self.items_base:List[PolyItem]=[]

        self.items_final:List[PolyItem]=[]

        self.items_d:List[PolyItem]=[]

        self.items_a:List[PolyItem]=[]

        self.items_imd:List[PolyItem]=[]

        self.base_u=None; self.final_u=None

        self.all_items_for_numbering:List[PolyItem]=[]

        self.id_to_point:List[Tuple[float,float]]=[]

        self._grid_step = SCALE_GRID_DEFAULTS[500]

        self._scale_den = 500

        self._dxf_text_h = DXF_TEXT_HEIGHT_MIN

        self._extra_title=True; self._extra_north=True

        self._extra_legend=True; self._extra_meta=True



        self.scene=QGraphicsScene(self)

        self.view=ZoomableView(self.scene)



        self.tabs=QTabWidget()

        self.tabs.setMinimumWidth(380)

        self.tabs.setTabPosition(QTabWidget.East)

        self._build_tables()



        split=QSplitter(Qt.Horizontal)

        split.addWidget(self.view); split.addWidget(self.tabs)

        split.setStretchFactor(0,1); split.setStretchFactor(1,0)

        self.setCentralWidget(split)



        tb=QToolBar("Main"); tb.setIconSize(QSize(18,18))

        tb.setMovable(False)

        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.addToolBar(Qt.TopToolBarArea, tb)



        def act(text, tip, slot):

            a=QAction(text, self)

            a.setToolTip(tip)

            a.triggered.connect(slot)

            tb.addAction(a)

            return a



        act("① 📂 Φόρτωση","1. Φόρτωση DXF", self.on_load)

        act("② 🧮 Υπολογισμοί","2. Υπολογισμός Δ/Α/(Αρχ-Δ) + έλεγχος", self.on_compute)

        act("③ 🔧 Ρυθμίσεις","3. Κλίμακα/Καννάβος/Κείμενα & Extras", self.on_settings)

        act("④ 🧊 Πολύγωνα & Layers","4. Ανάθεση layers ανά πολύγωνο", self.on_assign_layers)

        act("⑤ 📐 DXF","5. Εξαγωγή DXF", self.on_export_dxf)

        act("⑥ 📄 PDF","6. Εξαγωγή PDF πινάκων", self.on_export_pdf)

        act("⑦ 📦 ZIP","7. DXF→hash-PDF→υπογραφή→ZIP", self.on_zip_workflow)



        tb.addSeparator()

        act("🔢 Αρίθμηση","Αυτόματες τομές + μοναδική αρίθμηση κορυφών", self.on_number)

        act("🎯 Fit","Προσαρμογή όψης", self.on_fit)

        act("🧾 CSV","Εξαγωγή πινάκων CSV", self.on_export_csv)

        act("🌓 Θέμα","Light/Dark εναλλαγή", self.toggle_theme)



        self.lbl_status=QLabel("Έτοιμο")

        tb.addWidget(self.lbl_status)



        self.viewDock=QDockWidget("Εμφάνιση", self)

        self.viewDock.setAllowedAreas(Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)

        self.viewDock.setFeatures(QDockWidget.DockWidgetClosable|QDockWidget.DockWidgetMovable)

        self._build_view_dock()

        self.addDockWidget(Qt.LeftDockWidgetArea, self.viewDock)

        self.viewDock.hide()



        self.apply_ios_theme(light=True)

        self.redraw_scene()



    # ---------- Build tables ----------

    def _make_table(self):

        t=QTableWidget()

        t.setColumnCount(5)

        t.setHorizontalHeaderLabels(["Πολύγωνο","Εμβαδό","Περίμετρος","Κορυφές","Αποστάσεις"])

        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        t.verticalHeader().setVisible(False)

        t.setWordWrap(True)

        t.setEditTriggers(QTableWidget.NoEditTriggers)

        t.setSelectionBehavior(QTableWidget.SelectRows)

        t.setAlternatingRowColors(True)

        t.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        t.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        return t



    def _build_tables(self):

        self.tbl_initial=self._make_table()

        self.tbl_base=self._make_table()

        self.tbl_final=self._make_table()

        self.tbl_d=self._make_table()

        self.tbl_a=self._make_table()

        self.tbl_imd=self._make_table()

        self.tbl_dgm=QTableWidget()

        self._setup_dgm_table()

        for t,name in [

            (self.tbl_initial,"Αρχικά"),

            (self.tbl_base,"Βασικό"),

            (self.tbl_final,"Τελικό"),

            (self.tbl_d,"Δ-ι"),

            (self.tbl_a,"Α-ι"),

            (self.tbl_imd,"Αρχ-Δ"),

            (self.tbl_dgm,"ΤΔΓΜ")

        ]:

            self.tabs.addTab(t,name)



    def _setup_dgm_table(self):

        t=self.tbl_dgm

        t.setColumnCount(6)

        t.setHorizontalHeaderLabels(["α/α","ΑΠΟ ΚΑΕΚ","ΣΕ ΚΑΕΚ","Εμβαδό","κορυφές","Χαρακτηρισμός"])

        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        t.verticalHeader().setVisible(False)

        t.setEditTriggers(QTableWidget.NoEditTriggers)

        t.setWordWrap(True)

        t.setSelectionBehavior(QTableWidget.SelectRows)

        t.setAlternatingRowColors(True)

        t.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        t.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)



    # ---------- View dock ----------

    def _build_view_dock(self):

        w=QWidget()

        v=QVBoxLayout(w)

        v.setContentsMargins(8,8,8,8)

        v.setSpacing(6)

        self.chk_initial=QCheckBox("Αρχικά"); self.chk_initial.setChecked(True)

        self.chk_base=QCheckBox("Βασικό"); self.chk_base.setChecked(True)

        self.chk_final=QCheckBox("Τελικό"); self.chk_final.setChecked(True)

        self.chk_d=QCheckBox("Δ-ι"); self.chk_d.setChecked(True)

        self.chk_a=QCheckBox("Α-ι"); self.chk_a.setChecked(True)

        self.chk_imd=QCheckBox("Αρχ-Δ"); self.chk_imd.setChecked(True)

        self.chk_vertex_labels=QCheckBox("Αριθμοί κορυφών"); self.chk_vertex_labels.setChecked(True)

        self.chk_distances=QCheckBox("Αποστάσεις πλευρών"); self.chk_distances.setChecked(True)

        for c in (

            self.chk_initial,self.chk_base,self.chk_final,

            self.chk_d,self.chk_a,self.chk_imd,

            self.chk_vertex_labels,self.chk_distances

        ):

            c.toggled.connect(self.redraw_scene)

            v.addWidget(c)

        btn=QPushButton("Κλείσιμο")

        btn.clicked.connect(self.viewDock.hide)

        v.addWidget(btn)

        self.viewDock.setWidget(w)



    # ---------- Scale/grid helpers ----------

    def _parse_scale_den_str(self,s)->int:

        try:

            s=unicodedata.normalize("NFKC", s or "")

            nums=re.findall(r"(\d+)", s)

            return max(1,int(nums[-1])) if nums else 500

        except Exception:

            return 500

    def get_scale_den(self):

        return int(self._scale_den)

    def set_scale_den(self, den:int):

        self._scale_den = max(1, int(den))

        if self._scale_den in SCALE_GRID_DEFAULTS:

            self._grid_step = SCALE_GRID_DEFAULTS[self._scale_den]

        self.redraw_scene()

    def get_grid_step(self):

        return float(self._grid_step)

    def set_grid_step(self, step:float):

        self._grid_step = max(0.01, float(step))

        self.redraw_scene()

    def get_text_h(self):

        return float(self._dxf_text_h)

    def set_text_h(self, h:float):

        self._dxf_text_h = max(DXF_TEXT_HEIGHT_MIN, float(h))



    # ---------- Tables helpers ----------

    def _collect_dgm_rows(self):

        rows=[]

        for it in self.items_d:

            rows.append({

                "from": it.from_kaek or it.name,

                "to": it.to_kaek or "Τ-1",

                "area": float(it.polygon.area),

                "verts": format_vertices_cycle(it.point_ids),

                "char": "Δ"

            })

        for it in self.items_a:

            rows.append({

                "from": it.from_kaek or it.name,

                "to": it.to_kaek or "ΝΕΟ ΚΑΕΚ-?",

                "area": float(it.polygon.area),

                "verts": format_vertices_cycle(it.point_ids),

                "char": "Α"

            })

        return rows



    def rows_for_gui(self):

        rows_initial=rows_for_polys(self.items_initial,self.id_to_point)

        rows_base=rows_for_polys(self.items_base,self.id_to_point)

        rows_final=rows_for_polys(self.items_final,self.id_to_point)

        rows_d=rows_for_polys(self.items_d,self.id_to_point)

        rows_a=rows_for_polys(self.items_a,self.id_to_point)

        rows_imd=rows_for_polys(self.items_imd,self.id_to_point)

        groups={

            "pinakas_archika":rows_initial,

            "pinakas_vasiko":rows_base,

            "pinakas_teliko":rows_final,

            "pinakas_diekdikoumena":rows_d,

            "pinakas_afairoumena":rows_a,

            "pinakas_arch_minus_d":rows_imd

        }

        equalize_table_lengths(groups)

        return groups



    def set_table(self,tbl,rows):

        tbl.setRowCount(len(rows))

        for r,row in enumerate(rows):

            tbl.setItem(r,0,QTableWidgetItem(row.name))

            tbl.setItem(r,1,QTableWidgetItem(f"{row.area:.3f}" if row.name else ""))

            tbl.setItem(r,2,QTableWidgetItem(f"{row.perim:.3f}" if row.name else ""))

            tbl.setItem(r,3,QTableWidgetItem(row.verts))

            tbl.setItem(r,4,QTableWidgetItem(row.dists))

        tbl.resizeColumnsToContents()

        tbl.resizeRowsToContents()



    def populate_tables(self):

        g=self.rows_for_gui()

        self.set_table(self.tbl_initial,g["pinakas_archika"])

        self.set_table(self.tbl_base,g["pinakas_vasiko"])

        self.set_table(self.tbl_final,g["pinakas_teliko"])

        self.set_table(self.tbl_d,g["pinakas_diekdikoumena"])

        self.set_table(self.tbl_a,g["pinakas_afairoumena"])

        self.set_table(self.tbl_imd,g["pinakas_arch_minus_d"])

        self.populate_dgm()



    def populate_dgm(self):

        rows=self._collect_dgm_rows()

        t=self.tbl_dgm

        t.setRowCount(len(rows))

        for r,row in enumerate(rows):

            t.setItem(r,0,QTableWidgetItem(str(r+1)))

            t.setItem(r,1,QTableWidgetItem(row["from"]))

            t.setItem(r,2,QTableWidgetItem(row["to"]))

            t.setItem(r,3,QTableWidgetItem(f"{row['area']:.3f}"))

            t.setItem(r,4,QTableWidgetItem(row["verts"]))

            t.setItem(r,5,QTableWidgetItem(row["char"]))

        t.resizeColumnsToContents()

        t.resizeRowsToContents()



    # ---------- Scene ----------

    def _find_label_pos(self, base_pt:QPointF, placed_pts:List[QPointF], min_dist:float)->QPointF:

        dirs=[QPointF(1,0), QPointF(0,1), QPointF(-1,0), QPointF(0,-1),

              QPointF(1,1), QPointF(-1,1), QPointF(-1,-1), QPointF(1,-1)]

        step=min_dist*0.7

        def ok(p):

            return all(((p.x()-q.x())**2+(p.y()-q.y())**2)**0.5 >= min_dist for q in placed_pts)

        if ok(base_pt):

            return base_pt

        for ring in range(1,12):

            for d in dirs:

                cand=QPointF(base_pt.x()+d.x()*step*ring, base_pt.y()+d.y()*step*ring)

                if ok(cand):

                    return cand

        return QPointF(base_pt.x()+step*10, base_pt.y()+step*10)



    def redraw_scene(self):

        self.scene.clear()

        spacing = float(self._grid_step)



        pen_init  = QPen(QColor("#1f77b4"), 0)

        pen_base  = QPen(QColor("#ff7f0e"), 0)

        pen_final = QPen(QColor("#d62728"), 0)

        pen_imd   = QPen(QColor("#8c564b"), 0, Qt.DashLine)

        brush_d   = QBrush(QColor(44,160,44,50))

        brush_a   = QBrush(QColor(148,103,189,50))



        label_min_dist = max(GUI_LABEL_MIN_DIST_M, spacing*0.3)

        placed_label_centers: List[QPointF] = []



        def add_poly(it, pen, brush=None):

            coords=list(it.polygon.exterior.coords)

            if len(coords)<2:

                return

            path=QPainterPath(QPointF(coords[0][0], -coords[0][1]))

            for x,y in coords[1:]:

                path.lineTo(QPointF(x,-y))

            g=QGraphicsPathItem(path)

            g.setPen(pen)

            if brush is not None:

                g.setBrush(brush)

            self.scene.addItem(g)



            rp = it.polygon.representative_point()

            base_pt = QPointF(rp.x, -rp.y)

            pos = self._find_label_pos(base_pt, placed_label_centers, label_min_dist)

            placed_label_centers.append(pos)



            halo = QGraphicsTextItem(it.name)

            f = QFont("Arial"); f.setPixelSize(GUI_LABEL_FONT_PX)

            halo.setFont(f)

            halo.setDefaultTextColor(QColor(255,255,255))

            halo.setPos(pos.x()+1, pos.y()+1)

            halo.setZValue(999)

            halo.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)



            txt  = PolyNameLabelItem(it.name, it, self._on_label_renamed)

            txt.setPos(pos)

            txt.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)



            self.scene.addItem(halo)

            self.scene.addItem(txt)



            if getattr(self,'chk_vertex_labels',None) and self.chk_vertex_labels.isChecked() and self.id_to_point:

                for pid in it.point_ids:

                    px,py=self.id_to_point[pid-1]

                    self.scene.addItem(VertexMarkerItem(px,py,str(pid)))



            if getattr(self,'chk_distances',None) and self.chk_distances.isChecked() and it.point_ids and self.id_to_point:

                ring=list(it.polygon.exterior.coords)

                n=len(ring)-1

                for i in range(n):

                    a=ring[i]; b=ring[(i+1)%n]

                    L=math.hypot(b[0]-a[0], b[1]-a[1])

                    if L<=0.01:

                        continue

                    mx=(a[0]+b[0])/2.0

                    my=(a[1]+b[1])/2.0

                    txt_item = QGraphicsTextItem(f"{L:.2f}")

                    f2 = QFont("Arial"); f2.setPixelSize(7)

                    txt_item.setFont(f2)

                    txt_item.setDefaultTextColor(QColor(0,0,80))

                    txt_item.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)

                    txt_item.setPos(mx, -my)

                    txt_item.setZValue(900)

                    self.scene.addItem(txt_item)



        if getattr(self,'chk_initial',None) and self.chk_initial.isChecked():

            for it in self.items_initial:

                add_poly(it, pen_init)

        if getattr(self,'chk_base',None) and self.chk_base.isChecked():

            for it in self.items_base:

                add_poly(it, pen_base)

        if getattr(self,'chk_final',None) and self.chk_final.isChecked():

            for it in self.items_final:

                add_poly(it, pen_final)

        if getattr(self,'chk_d',None) and self.chk_d.isChecked():

            for it in self.items_d:

                add_poly(it, QPen(QColor("#2ca02c"),0), brush_d)

        if getattr(self,'chk_a',None) and self.chk_a.isChecked():

            for it in self.items_a:

                add_poly(it, QPen(QColor("#9467bd"),0), brush_a)

        if getattr(self,'chk_imd',None) and self.chk_imd.isChecked():

            for it in self.items_imd:

                add_poly(it, pen_imd, None)



        self.view.setSceneRect(self.scene.itemsBoundingRect())



    def _on_label_renamed(self):

        self.populate_tables()

        self.populate_dgm()



    def on_fit(self):

        self.view.fitInView(self.view.sceneRect(), Qt.KeepAspectRatio)



    # ---------- Actions ----------

    def _init_poly_layers(self, it:PolyItem):

        if not it.layers:

            key = it.role

            if key=="final":

                key="final_out"

            it.layers = list(DEFAULT_ROLE_LAYERS_MULTI.get(key, []))



    def on_load(self):

        fn,_=QFileDialog.getOpenFileName(self,"Επιλέξτε DXF","","DXF (*.dxf)")

        if not fn:

            return

        try:

            initials,bases,finals=load_from_dxf(fn)

        except Exception as e:

            QMessageBox.critical(self,"Σφάλμα",f"Αποτυχία ανάγνωσης DXF:\n{e}")

            return



        self.items_initial=[PolyItem("initial",f"Αρχ-{i+1}",make_valid(g)) for i,g in enumerate(initials)]

        self.items_base=[PolyItem("base",f"Β-{i+1}",make_valid(g)) for i,g in enumerate(bases)]

        self.items_final=[PolyItem("final",f"Τ-{i+1}",make_valid(g)) for i,g in enumerate(finals)]



        for it in (self.items_initial + self.items_base + self.items_final):

            self._init_poly_layers(it)



        self.items_d=[]; self.items_a=[]; self.items_imd=[]

        self.base_u=None; self.final_u=None

        self.all_items_for_numbering=[]; self.id_to_point=[]

        self._clear_tables()

        self.populate_dgm()

        self.on_compute()

        self.on_number()

        self.lbl_status.setText(

            f"Αρχ:{len(self.items_initial)} Βασ:{len(self.items_base)} Τελ:{len(self.items_final)}"

        )

        self.redraw_scene()

        self.on_fit()



    def on_compute(self):

        initials=[it.polygon for it in self.items_initial]

        bases=[it.polygon for it in self.items_base]

        finals=[it.polygon for it in self.items_final]

        claimed_parts, removed_parts, initial_minus_d, base_u, final_u = compute_claimed_and_removed(initials,bases,finals)

        self.base_u, self.final_u = base_u, final_u



        self.items_d=[]

        for k,(i_idx,p) in enumerate(claimed_parts,1):

            it=PolyItem("area_d",f"Δ-{k}",make_valid(p))

            it.from_kaek=f"Αρχ-{i_idx}"

            it.to_kaek="Τ-1" if self.items_final else "Τ-?"

            it.characteristic="Δ"

            self._init_poly_layers(it)

            self.items_d.append(it)



        self.items_a=[]

        for k,p in enumerate(removed_parts,1):

            it=PolyItem("area_a",f"Α-{k}",make_valid(p))

            it.from_kaek="Β-1" if self.items_base else "Β-?"

            it.to_kaek=f"ΝΕΟ ΚΑΕΚ-{k}"

            it.characteristic="Α"

            self._init_poly_layers(it)

            self.items_a.append(it)



        self.items_imd=[]

        counters={}

        for i_idx,p in initial_minus_d:

            counters[i_idx]=counters.get(i_idx,0)+1

            name=f"(Αρχ-{i_idx})-(Δ-{counters[i_idx]})"

            it=PolyItem("initial_minus_d",name,make_valid(p))

            self._init_poly_layers(it)

            self.items_imd.append(it)



        self.populate_tables()

        self.populate_dgm()

        self.all_items_for_numbering=self._all_items()

        ok,adiff=algebraic_check(

            self.base_u,

            self.final_u,

            [it.polygon for it in self.items_a],

            [(0,it.polygon) for it in self.items_d]

        )

        self.lbl_status.setText(

            "Έλεγχος: Β-Α+Δ = Τ ✔" if ok else f"Έλεγχος: Β-Α+Δ ≠ Τ ✖, Δ≈{adiff:.6f}"

        )

        self.redraw_scene()

        self.on_fit()



    def on_number(self):

        try:

            target=self.all_items_for_numbering if self.all_items_for_numbering else self._all_items()

            if not target:

                QMessageBox.information(self,"Προσοχή","Δεν υπάρχουν πολύγωνα για αρίθμηση.")

                return

            augment_intersections(target, tol=1e-7)

            target, self.id_to_point = assign_global_vertex_numbers(target, decimals=SNAP_DECIMALS)

            self.all_items_for_numbering=target

            self.populate_tables()

            self.populate_dgm()

            self.lbl_status.setText(

                f"Αρίθμηση: {len(self.id_to_point)} μοναδικά σημεία (στους {SNAP_DECIMALS} δεκ.)."

            )

            self.redraw_scene()

            self.on_fit()

        except Exception as e:

            QMessageBox.critical(self,"Σφάλμα Αρίθμησης",f"Η αρίθμηση απέτυχε:\n{e}")



    def on_assign_layers(self):

        items = self._all_items()

        if not items:

            QMessageBox.information(self,"Προσοχή","Δεν υπάρχουν πολύγωνα για ανάθεση layers.")

            return

        dlg = PolygonLayersDialog(self, items)

        if dlg.exec_()==QDialog.Accepted:

            self.redraw_scene()



    def on_export_csv(self):

        if not self.id_to_point:

            QMessageBox.information(self, "Προσοχή", "Κάνε πρώτα «Υπολογισμοί» και «Αρίθμηση».")

            return

        d = QFileDialog.getExistingDirectory(self, "Φάκελος για CSV")

        if not d:

            return

        groups = self.rows_for_gui()

        try:

            for key, rows in groups.items():

                out_path = os.path.join(d, f"{key}.csv")

                with open(out_path, "w", newline="", encoding="utf-8") as f:

                    w = csv.writer(f)

                    w.writerow(["Πολύγωνο", "Εμβαδό", "Περίμετρος", "Κορυφές", "Αποστάσεις"])

                    for r in rows:

                        w.writerow([

                            r.name,

                            f"{r.area:.3f}" if r.name else "",

                            f"{r.perim:.3f}" if r.name else "",

                            r.verts,

                            (r.dists or "").replace("\n"," | ")

                        ])

            dgm_rows = self._collect_dgm_rows()

            out_path = os.path.join(d, "pinakas_geometrikon_metavolon.csv")

            with open(out_path, "w", newline="", encoding="utf-8") as f:

                w = csv.writer(f)

                w.writerow(["α/α","ΑΠΟ ΚΑΕΚ","ΣΕ ΚΑΕΚ","Εμβαδό","κορυφές","Χαρακτηρισμός"])

                for i, row in enumerate(dgm_rows, start=1):

                    w.writerow([i, row["from"], row["to"], f"{row['area']:.3f}", row["verts"], row["char"]])

            QMessageBox.information(self, "ΟΚ", "CSV πινάκων αποθηκεύτηκαν.")

        except Exception as e:

            QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία αποθήκευσης CSV:\n{e}")



    def on_export_pdf(self):

        if not REPORTLAB_OK:

            QMessageBox.information(

                self,

                "PDF",

                "Εγκατέστησε reportlab (pip install reportlab) για PDF αναφορά."

            )

            return

        fn,_=QFileDialog.getSaveFileName(self,"Αποθήκευση PDF αναφοράς","","PDF (*.pdf)")

        if not fn:

            return

        try:

            self.export_pdf(fn)

            QMessageBox.information(self,"ΟΚ","PDF αποθηκεύτηκε.")

        except Exception as e:

            QMessageBox.critical(self,"Σφάλμα PDF",f"Αποτυχία PDF:\n{e}")



    def on_export_dxf(self):

        if not (self.items_initial or self.items_base or self.items_final or self.items_d or self.items_a):

            QMessageBox.information(self,"Προσοχή","Δεν υπάρχουν δεδομένα για εξαγωγή.")

            return

        fn, _ = QFileDialog.getSaveFileName(self, "Αποθήκευση DXF", "", "DXF R2018 (*.dxf)")

        if not fn:

            return

        try:

            self.export_dxf(fn)

            QMessageBox.information(self, "ΟΚ", "DXF αποθηκεύτηκε.")

        except Exception as e:

            QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία εξαγωγής DXF:\n{e}")



    def on_settings(self):

        dlg=SettingsDialog(

            self,

            get_scale=lambda: self.get_scale_den(),

            set_scale=self.set_scale_den,

            get_grid=lambda: self.get_grid_step(),

            set_grid=self.set_grid_step,

            get_text_h=lambda: self.get_text_h(),

            set_text_h=self.set_text_h,

            extras={

                "title": lambda: getattr(self,'_extra_title', True),

                "north": lambda: getattr(self,'_extra_north', True),

                "legend": lambda: getattr(self,'_extra_legend', True),

                "meta": lambda: getattr(self,'_extra_meta', True),

            }

        )

        if dlg.exec_()==QDialog.Accepted:

            v=dlg.values()

            new_den = self._parse_scale_den_str(v["scale"])

            self._scale_den = max(1, int(new_den))

            if self._scale_den in SCALE_GRID_DEFAULTS:

                self._grid_step = SCALE_GRID_DEFAULTS[self._scale_den]

            else:

                self._grid_step = float(v["grid"])

            self.set_text_h(v["text_h"])

            self._extra_title=v["title"]

            self._extra_north=v["north"]

            self._extra_legend=v["legend"]

            self._extra_meta=v["meta"]

            self.redraw_scene()



    def on_zip_workflow(self):

        if not (self.items_initial or self.items_base or self.items_final):

            QMessageBox.information(self, "Προσοχή", "Δεν υπάρχουν πολύγωνα. Φόρτωσε DXF και τρέξε Υπολογισμούς.")

            return

        if not SIGNING_OK:

            QMessageBox.critical(

                self,"Υπογραφή",

                "Λείπουν τα πακέτα pkcs11 / endesive / cryptography.\n"

                "Εγκατάσταση: pip install python-pkcs11 endesive cryptography"

            )

            return



        zip_path,_ = QFileDialog.getSaveFileName(self,"Αποθήκευση ZIP","","ZIP (*.zip)")

        if not zip_path:

            return

        base_dir = os.path.dirname(zip_path)

        base_name = os.path.splitext(os.path.basename(zip_path))[0]



        dxf_path = os.path.join(base_dir, f"{base_name}.dxf")

        hash_pdf_path = os.path.join(base_dir, f"{base_name}.pdf")

        signed_hash_pdf_path = os.path.join(base_dir, f"{base_name}_signed.pdf")



        try:

            self.export_dxf(dxf_path)

            hash_val = compute_sha512_hash(dxf_path)

            create_hash_only_pdf(hash_val, hash_pdf_path)

            pin, ok = QInputDialog.getText(

                self, "PIN USB Token",

                "Εισάγετε το PIN του USB token (μία φορά):",

                QLineEdit.Password

            )

        except Exception as e:

            QMessageBox.critical(self,"Σφάλμα",f"Αποτυχία πριν την υπογραφή:\n{e}")

            return



        if not ok or not pin:

            return



        session = None

        try:

            cert_der, privkey, session, owner_name = open_token_once(pin)

            sign_pdf_invisible(hash_pdf_path, signed_hash_pdf_path, privkey, cert_der)



            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:

                z.write(dxf_path, os.path.basename(dxf_path))

                z.write(signed_hash_pdf_path, f"{base_name}.pdf")



            QMessageBox.information(

                self,"ΟΚ",

                f"Το ZIP δημιουργήθηκε:\n{zip_path}\n\n"

                f"Υπογράφων: {owner_name}"

            )

        except Exception as e:

            QMessageBox.critical(self,"Σφάλμα υπογραφής/ZIP",f"{e}\n\n{traceback.format_exc()}")

        finally:

            if session is not None:

                try:

                    session.close()

                except Exception:

                    pass

            try:

                if os.path.exists(hash_pdf_path):

                    os.remove(hash_pdf_path)

            except Exception:

                pass



    # ---------- Export helpers ----------

    def _place_text(self, msp, text, xy, layer, height, rotation=None):

        e = msp.add_text(

            text,

            dxfattribs={"height": height, "layer": layer, "style": "ARIAL"}

        )

        x,y=xy

        if hasattr(e,"set_pos"):

            try:

                e.set_pos((x,y))

            except Exception:

                e.dxf.insert=(x,y,0)

        else:

            e.dxf.insert=(x,y,0)

        if rotation is not None:

            try:

                e.dxf.rotation=float(rotation)

            except Exception:

                pass

        return e



    def export_dxf(self, path:str):

        doc=ezdxf.new(setup=True)

        msp=doc.modelspace()

        try:

            if "ARIAL" not in doc.styles:

                doc.styles.add("ARIAL", font="arial.ttf")

        except Exception:

            pass



        used_layers=set(["TABLES","GRID","DIST-TEXT","LABEL","FRAME","FRAME_BLUE","KORYFES"])

        for it in self._all_items():

            if it.layers:

                used_layers.update(it.layers)

        for ln in sorted(used_layers|set(LAYER_ALIASES.keys())):

            ensure_layer_with_style(doc, ln)



        spacing=float(self._grid_step)

        base_text_h = max(DXF_TEXT_HEIGHT_MIN, spacing * DXF_TEXT_HEIGHT_FACTOR, self._dxf_text_h)



        def add_polyitem(it:PolyItem):

            coords=list(it.polygon.exterior.coords)

            if len(coords)<2:

                return

            layers = it.layers or []

            if not layers:

                key = it.role

                if key=="final":

                    key="final_out"

                layers = DEFAULT_ROLE_LAYERS_MULTI.get(key, [])

            for layer in layers:

                ensure_layer_with_style(doc, layer)

                msp.add_lwpolyline(

                    coords,

                    format="xy",

                    dxfattribs={"layer":layer,"closed":True}

                )



        for it in self.items_initial: add_polyitem(it)

        for it in self.items_base: add_polyitem(it)

        for it in self.items_final: add_polyitem(it)

        for it in self.items_d: add_polyitem(it)

        for it in self.items_a: add_polyitem(it)

        for it in self.items_imd: add_polyitem(it)



        for pt in self.id_to_point:

            msp.add_circle(

                center=(pt[0], pt[1], 0),

                radius=DXF_POINT_RADIUS,

                dxfattribs={"layer": "KORYFES"}

            )

        for idx,pt in enumerate(self.id_to_point,1):

            self._place_text(

                msp,

                str(idx),

                (pt[0]+DXF_POINT_RADIUS*1.2, pt[1]+DXF_POINT_RADIUS*1.2),

                "LABEL",

                base_text_h

            )



        placed=[]

        min_dist = spacing*0.6

        for it in self._all_items():

            rp=it.polygon.representative_point()

            bx,by=rp.x,rp.y

            dirs=[(1,0),(0,1),(-1,0),(0,-1),(1,1),(-1,1),(-1,-1),(1,-1)]

            pos=(bx,by)

            def ok(p):

                return all(math.hypot(p[0]-q[0], p[1]-q[1])>=min_dist for q in placed)

            if not ok(pos):

                step=min_dist*0.8

                for rad in range(1,15):

                    for dx,dy in dirs:

                        cand=(bx+dx*step*rad,by+dy*step*rad)

                        if ok(cand):

                            pos=cand

                            break

                    else:

                        continue

                    break

            placed.append(pos)

            self._place_text(msp, it.name, pos, "LABEL", base_text_h)



        self._export_unique_edge_distance_texts(msp, text_h=base_text_h)

        self._export_cross_grid_frame_and_coords(doc, msp, text_h=base_text_h, margin=spacing*0.5)

        tables_bbox = self._export_all_tables_as_grids(msp, spacing=spacing, text_h=base_text_h)

        if getattr(self,'_extra_title',True) or getattr(self,'_extra_legend',True) or getattr(self,'_extra_meta',True):

            self._export_extras_panel(msp, spacing=spacing, text_h=base_text_h, tables_bbox=tables_bbox)



        mism=validate_layers_exact(doc)

        if mism:

            raise RuntimeError("Layer style mismatch:\n"+"\n".join(mism))

        doc.saveas(path)



    def _bbox_all(self):

        polys=[it.polygon for it in self._all_items()]

        if not polys:

            return (0,0,100,100)

        minx=min(p.bounds[0] for p in polys)

        miny=min(p.bounds[1] for p in polys)

        maxx=max(p.bounds[2] for p in polys)

        maxy=max(p.bounds[3] for p in polys)

        return (minx,miny,maxx,maxy)



    def _frame_bbox(self, spacing:float, margin:float=10.0):

        raw_minx,raw_miny,raw_maxx,raw_maxy = self._bbox_all()

        xmin = math.floor((raw_minx - margin)/spacing)*spacing

        ymin = math.floor((raw_miny - margin)/spacing)*spacing

        xmax = math.ceil((raw_maxx + margin)/spacing)*spacing

        ymax = math.ceil((raw_maxy + margin)/spacing)*spacing

        return xmin,ymin,xmax,ymax



    def _draw_arrowhead(self,msp,tip_xy,dir_vec,size=0.6,layer="DIST-TEXT"):

        tx,ty=tip_xy

        dx,dy=dir_vec

        bx=tx-dx*size; by=ty-dy*size

        nx,ny=-dy,dx

        base_half=0.45*size

        p1=(bx+nx*base_half, by+ny*base_half, 0)

        p2=(bx-nx*base_half, by-ny*base_half, 0)

        tip3=(tx,ty,0)

        msp.add_solid([tip3,p1,p2], dxfattribs={"layer":layer})



    def _export_unique_edge_distance_texts(self,msp, text_h):

        ensure_layer_with_style(msp.doc,"DIST-TEXT")

        items=self._all_items()

        seen=set()

        min_edge_len=3.0*text_h

        pad=0.6*text_h

        char_w=0.60*text_h

        placed=[]

        def overlaps(a,b):

            ax1,ay1,ax2,ay2=a

            bx1,by1,bx2,by2=b

            return not (ax2<bx1 or bx2<ax1 or ay2<by1 or by2<ay1)

        def bbox(cx,cy,text):

            w=max(len(text)*char_w, char_w*2)

            h=text_h

            return (cx-w/2-pad, cy-h/2-pad, cx+w/2+pad, cy+h/2+pad)

        def place(text,mx,my,ang,nx,ny):

            trials=[]

            for o in (1.5*DXF_POINT_RADIUS, 3.0*DXF_POINT_RADIUS, 4.5*DXF_POINT_RADIUS):

                trials += [(mx+nx*o,my+ny*o,False),(mx-nx*o,my-ny*o,False)]

            tx,ty=ny,-nx

            trials += [(mx+tx*DXF_POINT_RADIUS,my+ty*DXF_POINT_RADIUS,False),

                       (mx-tx*DXF_POINT_RADIUS,my-ty*DXF_POINT_RADIUS,False)]

            trials += [(mx+nx*6*DXF_POINT_RADIUS,my+ny*6*DXF_POINT_RADIUS,True),

                       (mx-nx*6*DXF_POINT_RADIUS,my-ny*6*DXF_POINT_RADIUS,True)]

            for x,y,lead in trials:

                bb=bbox(x,y,text)

                if any(overlaps(bb,q) for q in placed):

                    continue

                if lead:

                    msp.add_line((mx,my,0),(x,y,0), dxfattribs={"layer":"DIST-TEXT"})

                    vx,vy=mx-x,my-y

                    L=math.hypot(vx,vy) or 1.0

                    self._draw_arrowhead(

                        msp,

                        (mx,my),

                        (vx/L,vy/L),

                        size=0.6*text_h,

                        layer="DIST-TEXT"

                    )

                self._place_text(msp,text,(x,y),"DIST-TEXT",text_h,rotation=ang)

                placed.append(bb)

                return True

            return False



        for it in items:

            ring=list(it.polygon.exterior.coords)

            n=len(ring)-1

            for i in range(n):

                a=ring[i]; b=ring[(i+1)%n]

                dx=b[0]-a[0]; dy=b[1]-a[1]

                L=math.hypot(dx,dy)

                if L<min_edge_len:

                    continue

                label=f"{L:.2f}"

                if it.point_ids and i<len(it.point_ids):

                    ida=it.point_ids[i]; idb=it.point_ids[(i+1)%n]

                    key=(min(ida,idb),max(ida,idb))

                    if key in seen:

                        continue

                    seen.add(key)

                    label=f"{ida}:{idb}={L:.2f}"

                mx=(a[0]+b[0])/2; my=(a[1]+b[1])/2

                ang=math.degrees(math.atan2(dy,dx))

                nx,ny=-dy,dx

                Ln=math.hypot(nx,ny) or 1.0

                nx,ny=nx/Ln,ny/Ln

                place(label,mx,my,ang,nx,ny)



    def _export_cross_grid_frame_and_coords(self,doc,msp, text_h, margin:float=10.0):

        ensure_layer_with_style(doc,"GRID")

        ensure_layer_with_style(doc,"LABEL")

        ensure_layer_with_style(doc,"FRAME")

        ensure_layer_with_style(doc,"FRAME_BLUE")



        den=int(self._scale_den)

        spacing=float(self._grid_step)



        minx,miny,maxx,maxy = self._frame_bbox(spacing, margin=margin)



        msp.add_lwpolyline(

            [(minx,miny),(maxx,miny),(maxx,maxy),(minx,maxy),(minx,miny)],

            format="xy",

            dxfattribs={"layer":"FRAME","closed":True}

        )



        arm = spacing*0.15 if spacing>0 else 0.2

        x = minx

        while x <= maxx + 1e-9:

            y = miny

            while y <= maxy + 1e-9:

                if x > minx + 1e-9:

                    x1 = max(x-arm, minx); x2 = x

                    msp.add_line((x1,y,0),(x2,y,0), dxfattribs={"layer":"GRID"})

                if x < maxx - 1e-9:

                    x1 = x; x2 = min(x+arm, maxx)

                    msp.add_line((x1,y,0),(x2,y,0), dxfattribs={"layer":"GRID"})

                if y > miny + 1e-9:

                    y1 = max(y-arm, miny); y2 = y

                    msp.add_line((x,y1,0),(x,y2,0), dxfattribs={"layer":"GRID"})

                if y < maxy - 1e-9:

                    y1 = y; y2 = min(y+arm, maxy)

                    msp.add_line((x,y1,0),(x,y2,0), dxfattribs={"layer":"GRID"})

                y += spacing

            x += spacing



        tick = spacing * 0.06

        coord_h = max(DXF_TEXT_HEIGHT_MIN, text_h * 0.7)



        x = minx

        while x <= maxx + 1e-9:

            msp.add_line((x,miny,0),(x,miny-tick,0), dxfattribs={"layer":"GRID"})

            self._place_text(

                msp,

                f"{x:.2f}",

                (x, miny - tick - coord_h*1.05),

                "LABEL",

                coord_h,

                rotation=90

            )

            x += spacing



        x = minx

        while x <= maxx + 1e-9:

            msp.add_line((x,maxy,0),(x,maxy+tick,0), dxfattribs={"layer":"GRID"})

            self._place_text(

                msp,

                f"{x:.2f}",

                (x, maxy + tick + coord_h*0.05),

                "LABEL",

                coord_h,

                rotation=90

            )

            x += spacing



        y = miny

        while y <= maxy + 1e-9:

            msp.add_line((minx,y,0),(minx-tick,y,0), dxfattribs={"layer":"GRID"})

            self._place_text(

                msp,

                f"{y:.2f}",

                (minx - tick*1.2, y - coord_h*0.4),

                "LABEL",

                coord_h

            )

            y += spacing



        y = miny

        while y <= maxy + 1e-9:

            msp.add_line((maxx,y,0),(maxx+tick,y,0), dxfattribs={"layer":"GRID"})

            self._place_text(

                msp,

                f"{y:.2f}",

                (maxx + tick*1.2, y - coord_h*0.4),

                "LABEL",

                coord_h

            )

            y += spacing



        bar=nice_round_scale_bar_length(den)

        base=(minx, miny-2*spacing, 0)

        msp.add_lwpolyline(

            [base,(base[0]+bar,base[1],0)],

            dxfattribs={"layer":"GRID"}

        )

        self._place_text(

            msp,

            f"Κλίμακα: 1:{int(den)}",

            (base[0],base[1]-spacing),

            "LABEL",

            text_h*1.2

        )



        if getattr(self, "_extra_north", True):

            cx = maxx - 0.6*spacing

            cy = maxy - 0.6*spacing

            stem_h = 0.35*spacing

            msp.add_line((cx,cy-stem_h,0),(cx,cy+stem_h,0), dxfattribs={"layer":"GRID"})

            msp.add_solid(

                [(cx, cy+stem_h,0),

                 (cx-0.08*spacing, cy+0.15*spacing,0),

                 (cx+0.08*spacing, cy+0.15*spacing,0)],

                dxfattribs={"layer":"GRID"}

            )

            self._place_text(

                msp,

                "N",

                (cx+0.09*spacing, cy+stem_h*1.05),

                "LABEL",

                text_h*1.0

            )



        outer_off = 0.25 * spacing

        oxmin = minx - outer_off

        oymin = miny - outer_off

        oxmax = maxx + outer_off

        oymax = maxy + outer_off

        msp.add_lwpolyline(

            [(oxmin,oymin),(oxmax,oymin),(oxmax,oymax),(oxmin,oymax),(oxmin,oymin)],

            format="xy",

            dxfattribs={"layer":"FRAME_BLUE","closed":True}

        )



    def _export_extras_panel(self, msp, spacing:float, text_h:float, tables_bbox:Tuple[float,float,float,float]):

        doc = msp.doc

        ensure_layer_with_style(doc,"GRID")

        ensure_layer_with_style(doc,"LABEL")



        minx_t,miny_t,maxx_t,maxy_t = tables_bbox

        panel_x = maxx_t + spacing*0.8

        y       = maxy_t



        box_w = 1.1*spacing

        box_h = 0.7*spacing



        def rect(x1,y1,x2,y2,layer="GRID"):

            msp.add_lwpolyline(

                [(x1,y1),(x2,y1),(x2,y2),(x1,y2),(x1,y1)],

                format="xy",

                dxfattribs={"layer":layer,"closed":True}

            )



        if getattr(self,'_extra_title',True):

            rect(panel_x, y-box_h, panel_x+box_w, y, "GRID")

            self._place_text(

                msp,

                "Τίτλος Σχεδίου",

                (panel_x+0.18*spacing, y-0.52*box_h),

                "LABEL",

                text_h

            )

            y -= (box_h + 0.12*spacing)



        if getattr(self,'_extra_legend',True):

            rows = [

                ("PST_KAEK","Αρχικά/Βασικό"),

                ("BOUND_IMPL","Τελικό / Αρχ-Δ (όριο)"),

                ("TOPO_PROP","Τελικό / Αρχ-Δ (τοπογρ.)"),

                ("DGM_PROP_FINAL","Τελικό / Αρχ-Δ (χώρος)"),

                ("AREA_D","Διεκδικούμενα"),

                ("AREA_A","Αφαιρούμενα"),

            ]

            height = max(box_h, 0.32*spacing*len(rows)+0.20*spacing)

            rect(panel_x, y-height, panel_x+box_w, y, "GRID")

            yy = y - 0.22*spacing

            for ln, txt in rows:

                try_col = LAYER_STYLE.get(ln,{}).get("color",7)

                msp.add_line(

                    (panel_x+0.07*spacing,yy,0),

                    (panel_x+0.32*spacing,yy,0),

                    dxfattribs={"layer":"GRID", "color": try_col}

                )

                self._place_text(

                    msp,

                    f"{txt} ({ln})",

                    (panel_x+0.38*spacing, yy-0.10*spacing),

                    "LABEL",

                    text_h*0.85

                )

                yy -= 0.32*spacing

            y -= (height + 0.12*spacing)



        if getattr(self,'_extra_meta',True):

            rect(panel_x, y-box_h*1.1, panel_x+box_w, y, "GRID")

            self._place_text(

                msp,

                f"Ημ/νία: {datetime.date.today().isoformat()}",

                (panel_x+0.09*spacing, y-0.32*box_h),

                "LABEL",

                text_h*0.85

            )

            self._place_text(

                msp,

                "Συντάκτης: ____________",

                (panel_x+0.09*spacing, y-0.60*box_h),

                "LABEL",

                text_h*0.85

            )

            self._place_text(

                msp,

                "Έργο: ____________",

                (panel_x+0.09*spacing, y-0.88*box_h),

                "LABEL",

                text_h*0.85

            )



    def _export_all_tables_as_grids(self,msp, spacing:float, text_h:float)->Tuple[float,float,float,float]:

        ensure_layer_with_style(msp.doc,"TABLES")



        total_w = DXF_TABLE_TOTAL_W_FACTOR * spacing

        cell_h  = DXF_TABLE_CELL_H_FACTOR  * spacing



        margin1 = 0.78 * spacing

        margin2 = 0.25 * spacing



        frame_minx, frame_miny, frame_maxx, frame_maxy = self._frame_bbox(spacing, margin=spacing*0.5)

        outer_off = 0.25 * spacing



        tables_minx = float("inf")

        tables_miny = float("inf")

        tables_maxx = float("-inf")

        tables_maxy = float("-inf")



        start_x = frame_maxx + outer_off + spacing * 0.8

        top_y   = frame_maxy - cell_h*1.5

        bottom_y = frame_miny + cell_h*1.5



        gap_y = cell_h * 0.8

        gap_x = spacing * 0.8



        def update_tables_bbox(x1,y1,x2,y2):

            nonlocal tables_minx, tables_miny, tables_maxx, tables_maxy

            tables_minx = min(tables_minx, x1, x2)

            tables_miny = min(tables_miny, y1, y2)

            tables_maxx = max(tables_maxx, x1, x2)

            tables_maxy = max(tables_maxy, y1, y2)



        def rect(x1,y1,x2,y2,layer="TABLES"):

            msp.add_lwpolyline(

                [(x1,y1),(x2,y1),(x2,y2),(x1,y2),(x1,y1)],

                format="xy",

                dxfattribs={"layer":layer,"closed":True}

            )

            update_tables_bbox(x1,y1,x2,y2)



        def center_text_in_cell(x1,y1,x2,y2,text,height_scale=1.0):

            if not text:

                return

            th = max(text_h*height_scale, DXF_TEXT_HEIGHT_MIN)

            cx = (x1+x2)/2.0

            cy = (y1+y2)/2.0 - th*0.4

            self._place_text(msp, text, (cx, cy), "TABLES", th)

            update_tables_bbox(x1,y1,x2,y2)



        def left_text_in_cell(x1,y1,x2,y2,text,height_scale=1.0, margin=0.0):

            if not text:

                return

            th = max(text_h*height_scale, DXF_TEXT_HEIGHT_MIN)

            cx = x1 + margin

            cy = (y1+y2)/2.0 - th*0.4

            self._place_text(msp, text, (cx, cy), "TABLES", th)

            update_tables_bbox(x1,y1,x2,y2)



        def distance_tokens_for_item(it:PolyItem)->List[str]:

            tokens=[]

            if not it.point_ids or not self.id_to_point:

                return tokens

            ids=it.point_ids

            n=len(ids)

            for i in range(n):

                a=ids[i]; b=ids[(i+1)%n]

                pa=self.id_to_point[a-1]; pb=self.id_to_point[b-1]

                d=math.hypot(pa[0]-pb[0], pa[1]-pb[1])

                tokens.append(f"{a}-{b}: {d:.2f}")

            return tokens



        current_x = start_x

        current_y = top_y



        def ensure_column_space(table_height_est:float):

            nonlocal current_x, current_y

            if current_y - table_height_est < bottom_y:

                current_x += total_w + gap_x

                current_y = top_y



        def draw_section(title:str, items:List[PolyItem]):

            nonlocal current_x, current_y

            if not items:

                return

            ensure_column_space(cell_h*2)

            title_th = max(text_h*1.05, DXF_TEXT_HEIGHT_MIN)

            title_x  = current_x + 0.72*spacing

            title_y  = current_y - 0.14*spacing

            self._place_text(msp, title, (title_x, title_y), "TABLES", title_th)

            update_tables_bbox(current_x, current_y, current_x+total_w, current_y)

            current_y -= cell_h*1.2



            for it in items:

                tokens = distance_tokens_for_item(it)

                dist_rows = max(1, (len(tokens)+3)//4) if tokens else 1

                table_height = (2 + dist_rows)*cell_h + gap_y

                ensure_column_space(table_height)



                y2 = current_y

                y1 = y2 - cell_h

                rect(current_x, y1, current_x+total_w, y2, "TABLES")

                left_text_in_cell(

                    current_x, y1, current_x+total_w, y2,

                    f"Πολύγωνο {it.name}",

                    height_scale=1.0,

                    margin=margin1

                )

                current_y = y1



                verts_str = format_vertices_cycle(it.point_ids)

                area = float(it.polygon.area)

                per  = float(it.polygon.length)

                info_txt = f"Σημεία {verts_str}, Εμβαδόν: {area:.2f} τ.μ, Περίμετρος: {per:.2f} μ"

                y2 = current_y

                y1 = y2 - cell_h

                rect(current_x, y1, current_x+total_w, y2, "TABLES")

                left_text_in_cell(

                    current_x, y1, current_x+total_w, y2,

                    info_txt,

                    height_scale=0.9,

                    margin=margin2

                )

                current_y = y1



                col_w = total_w / 4.0

                idx = 0

                for _ in range(dist_rows):

                    y2 = current_y

                    y1 = y2 - cell_h

                    for c in range(4):

                        x1 = current_x + col_w*c

                        x2 = x1 + col_w

                        rect(x1,y1,x2,y2,"TABLES")

                        txt = tokens[idx] if idx < len(tokens) else ""

                        center_text_in_cell(x1,y1,x2,y2, txt, height_scale=0.85)

                        idx += 1

                    current_y = y1



                current_y -= gap_y

            current_y -= gap_y*0.5



        draw_section("ΑΡΧΙΚΑ ΠΟΛΥΓΩΝΑ", self.items_initial)

        draw_section("ΒΑΣΙΚΟ ΠΟΛΥΓΩΝΟ", self.items_base)

        draw_section("ΤΕΛΙΚΟ ΠΟΛΥΓΩΝΟ", self.items_final)

        draw_section("ΔΙΕΚΔΙΚΟΥΜΕΝΑ (Δ)", self.items_d)

        draw_section("ΑΦΑΙΡΟΥΜΕΝΑ (Α)", self.items_a)

        draw_section("ΑΡΧΙΚΑ ΜΕΤΑ ΤΗΝ ΑΦΑΙΡΕΣΗ Δ (Αρχ-Δ)", self.items_imd)



        dgm_rows = self._collect_dgm_rows()

        if dgm_rows:

            est_height = (1 + len(dgm_rows))*cell_h + gap_y*2

            ensure_column_space(est_height)



            title = "ΠΙΝΑΚΑΣ ΓΕΩΜΕΤΡΙΚΩΝ ΜΕΤΑΒΟΛΩΝ (ΤΔΓΜ)"

            title_th = max(text_h*1.05, DXF_TEXT_HEIGHT_MIN)

            title_x  = current_x + 0.72*spacing

            title_y  = current_y - 0.14*spacing

            self._place_text(msp, title, (title_x, title_y), "TABLES", title_th)

            update_tables_bbox(current_x, current_y, current_x+total_w, current_y)

            current_y -= cell_h*1.2



            headers = ["α/α","ΑΠΟ ΚΑΕΚ","ΣΕ ΚΑΕΚ","Εμβαδό","κορυφές","Χαρακτηρισμός"]

            col_w = total_w / len(headers)



            y2 = current_y

            y1 = y2 - cell_h

            for i,hdr in enumerate(headers):

                x1 = current_x + col_w*i

                x2 = x1 + col_w

                rect(x1,y1,x2,y2,"TABLES")

                center_text_in_cell(x1,y1,x2,y2,hdr,height_scale=0.9)

            current_y = y1



            for i,row in enumerate(dgm_rows, start=1):

                if current_y - cell_h < bottom_y:

                    current_x += total_w + gap_x

                    current_y = top_y

                    y2 = current_y

                    y1 = y2 - cell_h

                    for ci,hdr in enumerate(headers):

                        x1 = current_x + col_w*ci

                        x2 = x1 + col_w

                        rect(x1,y1,x2,y2,"TABLES")

                        center_text_in_cell(x1,y1,x2,y2,hdr,height_scale=0.9)

                    current_y = y1



                y2 = current_y

                y1 = y2 - cell_h

                values = [

                    str(i),

                    row["from"],

                    row["to"],

                    f"{row['area']:.2f}",

                    row["verts"],

                    row["char"],

                ]

                for c,val in enumerate(values):

                    x1 = current_x + col_w*c

                    x2 = x1 + col_w

                    rect(x1,y1,x2,y2,"TABLES")

                    center_text_in_cell(x1,y1,x2,y2,val,height_scale=0.85)

                current_y = y1



            current_y -= gap_y



        if self.id_to_point:

            est_height = (1 + len(self.id_to_point))*cell_h + gap_y*2

            ensure_column_space(est_height)



            title = "ΠΙΝΑΚΑΣ ΣΥΝΤΕΤΑΓΜΕΝΩΝ"

            title_th = max(text_h*1.05, DXF_TEXT_HEIGHT_MIN)

            title_x  = current_x + 0.72*spacing

            title_y  = current_y - 0.14*spacing

            self._place_text(msp, title, (title_x, title_y), "TABLES", title_th)

            update_tables_bbox(current_x, current_y, current_x+total_w, current_y)

            current_y -= cell_h*1.2



            headers = ["ID","X","Y"]

            col_w = total_w / len(headers)



            y2 = current_y

            y1 = y2 - cell_h

            for i,hdr in enumerate(headers):

                x1 = current_x + col_w*i

                x2 = x1 + col_w

                rect(x1,y1,x2,y2,"TABLES")

                center_text_in_cell(x1,y1,x2,y2,hdr,height_scale=0.9)

            current_y = y1



            for i,(xv,yv) in enumerate(self.id_to_point, start=1):

                if current_y - cell_h < bottom_y:

                    current_x += total_w + gap_x

                    current_y = top_y

                    y2 = current_y

                    y1 = y2 - cell_h

                    for ci,hdr in enumerate(headers):

                        x1 = current_x + col_w*ci

                        x2 = x1 + col_w

                        rect(x1,y1,x2,y2,"TABLES")

                        center_text_in_cell(x1,y1,x2,y2,hdr,height_scale=0.9)

                    current_y = y1



                y2 = current_y

                y1 = y2 - cell_h

                values = [str(i), f"{xv:.3f}", f"{yv:.3f}"]

                for c,val in enumerate(values):

                    x1 = current_x + col_w*c

                    x2 = x1 + col_w

                    rect(x1,y1,x2,y2,"TABLES")

                    center_text_in_cell(x1,y1,x2,y2,val,height_scale=0.85)

                current_y = y1



        if tables_minx == float("inf"):

            raw_minx,raw_miny,raw_maxx,raw_maxy = self._bbox_all()

            return (raw_minx,raw_miny,raw_maxx,raw_maxy)

        return (tables_minx,tables_miny,tables_maxx,tables_maxy)



    def export_pdf(self, path:str):

        groups=self.rows_for_gui()

        dgm=self._collect_dgm_rows()

        c=pdf_canvas.Canvas(path, pagesize=A4)

        W,H=A4

        m=15*mm

        y=H-m

        def line(txt, size=9, leading=12):

            nonlocal y

            if y<40*mm:

                c.showPage()

                y=H-m

            c.setFont("Helvetica", size)

            c.drawString(m, y, txt)

            y-=leading

        line("Αναφορά Πινάκων ΤΔ/ΔΓΜ", 12, 16)

        line(f"Ημ/νία: {datetime.date.today().isoformat()}", 9, 14)

        y-=6

        def dump(title, rows):

            line(title, 11, 15)

            line("Πολύγωνο | Εμβαδό | Περίμετρος | Κορυφές | Αποστάσεις", 8, 12)

            for r in rows:

                ds=(r.dists or "").replace("\n"," | ")

                line(f"{r.name} | {r.area:.3f} | {r.perim:.3f} | {r.verts} | {ds}", 8, 12)

            line("-"*90, 8, 12)

        dump("ΠΙΝΑΚΑΣ ΑΡΧΙΚΩΝ", groups["pinakas_archika"])

        dump("ΠΙΝΑΚΑΣ ΒΑΣΙΚΟΥ", groups["pinakas_vasiko"])

        dump("ΠΙΝΑΚΑΣ ΤΕΛΙΚΟΥ", groups["pinakas_teliko"])

        dump("ΠΙΝΑΚΑΣ ΔΙΕΚΔΙΚΟΥΜΕΝΩΝ (Δ)", groups["pinakas_diekdikoumena"])

        dump("ΠΙΝΑΚΑΣ ΑΦΑΙΡΟΥΜΕΝΩΝ (Α)", groups["pinakas_afairoumena"])

        dump("ΠΙΝΑΚΑΣ ΑΡΧ-Δ", groups["pinakas_arch_minus_d"])

        if dgm:

            line("ΠΙΝΑΚΑΣ ΓΕΩΜΕΤΡΙΚΩΝ ΜΕΤΑΒΟΛΩΝ (ΤΔΓΜ)", 11, 15)

            line("α/α | ΑΠΟ ΚΑΕΚ | ΣΕ ΚΑΕΚ | Εμβαδό | κορυφές | Χαρακτηρισμός", 8, 12)

            for i,row in enumerate(dgm,1):

                line(

                    f"{i} | {row['from']} | {row['to']} | "

                    f"{row['area']:.3f} | {row['verts']} | {row['char']}",

                    8, 12

                )

        c.showPage()

        c.save()



    # ---------- Theme ----------

    def apply_ios_theme(self, light=True):

        base_bg = "#f7f7f8" if light else "#0f1115"

        base_fg = "#0d0e10" if light else "#eaeef5"

        panel_bg= "#ffffffcc" if light else "#1a1f29cc"

        sel     = "#dfe8ff" if light else "#203a72"

        self.setStyleSheet(f"""

            QMainWindow {{

                background: {base_bg};

                color: {base_fg};

            }}

            QToolBar {{

                background: {panel_bg};

                border: 0px;

                padding: 4px;

            }}

            QDockWidget::title {{

                background: {panel_bg};

                padding: 4px;

            }}

            QLabel, QCheckBox, QTableWidget, QTabWidget::pane {{

                color: {base_fg};

            }}

            QTableWidget {{

                gridline-color: #c8c8c8;

                font-size: 11px;

            }}

            QHeaderView::section {{

                background: {panel_bg};

                padding: 4px;

                font-weight: 600;

            }}

            QTabBar::tab {{

                padding: 6px 10px;

                margin: 2px;

            }}

            QPushButton {{

                background: {panel_bg};

                border: 1px solid #9aa4b1;

                border-radius: 8px;

                padding: 4px 10px;

            }}

            QPushButton:hover {{

                border-color: #007aff;

            }}

            QComboBox, QDoubleSpinBox {{

                background: {panel_bg};

            }}

            QTableWidget::item:selected {{

                background: {sel};

            }}

        """)



    def toggle_theme(self):

        light = not hasattr(self, "_theme_dark") or self._theme_dark

        self._theme_dark = not light

        self.apply_ios_theme(light=light)



    # ---------- Helpers ----------

    def _all_items(self)->List[PolyItem]:

        return (

            self.items_initial

            + self.items_base

            + self.items_final

            + self.items_d

            + self.items_a

            + self.items_imd

        )



    def _clear_tables(self):

        for t in (

            self.tbl_initial,self.tbl_base,self.tbl_final,

            self.tbl_d,self.tbl_a,self.tbl_imd,self.tbl_dgm

        ):

            t.setRowCount(0)



# ===================== main =====================

def main():

    app=QApplication(sys.argv)

    f=app.font(); f.setPointSize(10); app.setFont(f)

    w=MainWindow()

    w.show()

    sys.exit(app.exec_())



if __name__=="__main__":

    main()
