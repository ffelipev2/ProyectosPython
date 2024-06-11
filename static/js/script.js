$(document).ready(function() {
            $('#uploadForm').on('submit', function(e) {
                e.preventDefault();
                var formData = new FormData(this);
                $.ajax({
                    type: 'POST',
                    url: '/',
                    data: formData,
                    processData: false,
                    contentType: false,
                    success: function(response) {
                        if (response === 'Archivo subido exitosamente') {
                            swal({
                                title: "Éxito",
                                text: "Archivo subido exitosamente",
                                icon: "success",
                                button: "OK",
                            }).then(() => {
                                location.reload();
                            });
                        } else {
                            swal({
                                title: "Error",
                                text: response,
                                icon: "error",
                                button: "OK",
                            });
                        }
                    }
                });
            });
        });