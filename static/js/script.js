// Initialize tooltips and popovers when document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Format CNIC input (if exists)
    const cnicInput = document.getElementById('cnic');
    if (cnicInput) {
        cnicInput.addEventListener('input', function(e) {
            // Remove non-digits
            let value = e.target.value.replace(/\D/g, '');
            
            // Limit to 13 digits
            if (value.length > 13) {
                value = value.slice(0, 13);
            }
            
            // Update input value
            e.target.value = value;
        });
    }
    
    // Format phone number input (if exists)
    const phoneInput = document.getElementById('phone');
    if (phoneInput) {
        phoneInput.addEventListener('input', function(e) {
            // Remove non-digits and dashes
            let value = e.target.value.replace(/[^\d-]/g, '');
            
            // Update input value
            e.target.value = value;
        });
    }
});

// Function to print voucher (demonstration)
function printVoucher(voucherId) {
    // This is just a simple demonstration of how you might handle printing
    // In a real app, you would likely have a more sophisticated approach
    
    // Create a "print view" of the voucher
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <html>
        <head>
            <title>Donation Voucher #${voucherId}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .voucher { border: 1px solid #ccc; padding: 20px; max-width: 800px; margin: 0 auto; }
                .header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
                .title { font-size: 24px; font-weight: bold; }
                .row { display: flex; margin-bottom: 10px; }
                .label { font-weight: bold; width: 150px; }
                .value { flex: 1; }
                .footer { margin-top: 50px; display: flex; justify-content: space-between; }
                .signature { width: 200px; border-top: 1px solid #333; text-align: center; padding-top: 5px; }
                @media print {
                    body { margin: 0; }
                    button { display: none; }
                }
            </style>
        </head>
        <body>
            <div class="voucher">
                <div class="header">
                    <div class="title">DONATION VOUCHER</div>
                    <div>Voucher #${voucherId}</div>
                </div>
                
                <div class="content">
                    <div class="row">
                        <div class="label">Date:</div>
                        <div class="value">${new Date().toLocaleDateString()}</div>
                    </div>
                    <div class="row">
                        <div class="label">Recipient:</div>
                        <div class="value">[Recipient Name]</div>
                    </div>
                    <div class="row">
                        <div class="label">CNIC:</div>
                        <div class="value">[Recipient CNIC]</div>
                    </div>
                    <div class="row">
                        <div class="label">Donation Type:</div>
                        <div class="value">[Donation Type]</div>
                    </div>
                    <div class="row">
                        <div class="label">Amount:</div>
                        <div class="value">Rs. [Amount]</div>
                    </div>
                    <div class="row">
                        <div class="label">Mode:</div>
                        <div class="value">[Donation Mode]</div>
                    </div>
                </div>
                
                <div class="footer">
                    <div class="signature">Recipient Signature</div>
                    <div class="signature">Authorized Signature</div>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 20px;">
                <button onclick="window.print()">Print Voucher</button>
                <button onclick="window.close()">Close</button>
            </div>
        </body>
        </html>
    `);
    printWindow.document.close();
}
