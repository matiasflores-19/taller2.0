        let currentFile = null;
        let currentPatente = null;

        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const processButton = document.getElementById('processButton');
        const selectedFile = document.getElementById('selectedFile');
        const fileName = document.getElementById('fileName');
        const imagePreview = document.getElementById('imagePreview');

        // Drag and drop functionality
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFileSelect(files);
            }
        });

        // Handle file selection
        function handleFileSelect(files) {
            if (files.length > 0) {
                const file = files[0];
                
                // Check if file is an image
                if (!file.type.match('image.*')) {
                    alert('Por favor selecciona un archivo de imagen (JPEG, PNG, etc.)');
                    return;
                }
                
                currentFile = file;
                fileName.textContent = file.name;
                selectedFile.style.display = 'block';
                processButton.disabled = false;
                
                // Show image preview
                const reader = new FileReader();
                reader.onload = function(e) {
                    imagePreview.src = e.target.result;
                    imagePreview.style.display = 'block';
                };
                reader.readAsDataURL(file);
                
                document.getElementById('patenteResult').innerHTML = '<p>Imagen cargada. Haz clic en "Procesar Patente"</p>';
            }
        }

        // Process image
        function processImage() {
            if (!currentFile) {
                alert('Primero selecciona una imagen');
                return;
            }

            const loading = document.getElementById('loading');
            const patenteResult = document.getElementById('patenteResult');
            
            processButton.disabled = true;
            loading.style.display = 'block';
            
            const formData = new FormData();
            formData.append('image', currentFile);

            fetch('/api/upload_image', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (data.patente) {
                        currentPatente = data.patente;
                        
                        if (data.existe) {
                            // Vehículo ya registrado
                            showVehicleInfo(data.vehiculo);
                            patenteResult.innerHTML = `
                                <div class="patente">${data.patente}</div>
                                <div class="status registrado">✅ YA REGISTRADO</div>
                            `;
                        } else {
                            // Nuevo vehículo
                            showVehicleForm(data.patente);
                            patenteResult.innerHTML = `
                                <div class="patente">${data.patente}</div>
                                <div class="status nuevo">🆕 NUEVO VEHÍCULO</div>
                            `;
                        }
                    } else {
                        patenteResult.innerHTML = `
                            <div style="color: #e74c3c;">❌ No se detectó patente</div>
                            <p>Intenta con una imagen más clara de la patente</p>
                            <ul style="text-align: left; margin: 10px 0;">
                                <li>Buena iluminación</li>
                                <li>Enfoque nítido</li>
                                <li>Patente completa en el marco</li>
                            </ul>
                        `;
                    }
                } else {
                    patenteResult.innerHTML = `
                        <div style="color: #e74c3c;">❌ Error: ${data.error}</div>
                    `;
                }
            })
            .catch(error => {
                patenteResult.innerHTML = `
                    <div style="color: #e74c3c;">❌ Error de conexión</div>
                `;
                console.error('Error:', error);
            })
            .finally(() => {
                processButton.disabled = false;
                loading.style.display = 'none';
            });
        }
        
        function showVehicleForm(patente) {
            document.getElementById('formVehiculo').style.display = 'block';
            document.getElementById('vehiculoInfo').style.display = 'none';
            document.getElementById('patente').value = patente;
        }
        
        function showVehicleInfo(vehiculo) {
            document.getElementById('formVehiculo').style.display = 'none';
            document.getElementById('vehiculoInfo').style.display = 'block';
            
            document.getElementById('infoDuenio').textContent = vehiculo.duenio;
            document.getElementById('infoVehiculo').textContent = vehiculo.vehiculo;
            document.getElementById('infoFalla').textContent = vehiculo.falla;
            document.getElementById('infoEmail').textContent = vehiculo.email;
            document.getElementById('infoEstado').textContent = vehiculo.estado;
        }
        
        // Manejar envío del formulario
        document.getElementById('vehicleForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = {
                patente: document.getElementById('patente').value,
                duenio: document.getElementById('duenio').value,
                vehiculo: document.getElementById('vehiculo').value,
                falla: document.getElementById('falla').value,
                email: document.getElementById('email').value
            };
            
            fetch('/api/guardar_vehiculo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('✅ Vehículo guardado correctamente');
                    // Recargar para mostrar la información
                    location.reload();
                } else {
                    alert('❌ Error: ' + data.error);
                }
            })
            .catch(error => {
                alert('❌ Error de conexión');
                console.error('Error:', error);
            });
        });
