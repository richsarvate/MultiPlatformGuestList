/**
 * Venmo Manager - Handle Venmo payments and integrations
 */

class VenmoManager {
    openVenmoPayment(venmoHandle, amount) {
        // Clean the handle (remove @ if present)
        const cleanHandle = venmoHandle.replace('@', '').trim();
        
        if (!cleanHandle) {
            alert('Invalid Venmo handle');
            return;
        }

        // Get venue and show date for payment description
        const venue = document.getElementById('venue')?.value || 'Comedy Show';
        const showDate = document.getElementById('show-date')?.value || '';
        
        // Create descriptive payment note
        let paymentDescription = venue;
        if (showDate) {
            paymentDescription += ` - ${showDate}`;
        }
        
        // Venmo URL scheme for payments
        const note = encodeURIComponent(paymentDescription);
        const venmoUrl = `venmo://paycharge?txn=pay&recipients=${cleanHandle}&amount=${amount}&note=${note}`;
        
        // For web browsers, we'll use the Venmo web interface
        const webUrl = `https://venmo.com/${cleanHandle}?amount=${amount}&note=${note}`;
        
        // Try to open the mobile app first, fallback to web
        try {
            // Create a hidden iframe to try the app URL
            const iframe = document.createElement('iframe');
            iframe.style.display = 'none';
            iframe.src = venmoUrl;
            document.body.appendChild(iframe);
            
            // Remove iframe after a short delay
            setTimeout(() => {
                document.body.removeChild(iframe);
            }, 100);
            
            // Also open web version as fallback
            setTimeout(() => {
                window.open(webUrl, '_blank');
            }, 500);
            
        } catch (error) {
            // Fallback to web version
            window.open(webUrl, '_blank');
        }
        
        console.log(`Opening Venmo payment: @${cleanHandle} for $${amount}`);
    }

    openCapitalOneZelle(amount, zelleEmail, memo, venue, showDate) {
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        
        if (isMobile) {
            // Mobile - try to open Capital One app directly
            alert(`Opening Capital One app...\n\nSend Zelle payment:\n• To: ${zelleEmail}\n• Amount: $${amount}\n• Memo: ${memo}\n\nIf the app doesn't open, open Capital One manually and go to Zelle.`);
            
            // Try to open Capital One app
            setTimeout(() => {
                window.location.href = 'https://apps.apple.com/us/app/capital-one-mobile/id407558537';
            }, 100);
            
        } else {
            // Desktop - open Capital One sign-in page and show instructions
            window.open('https://verified.capitalone.com/auth/signin', '_blank');
            
            setTimeout(() => {
                alert(`Capital One opened in new tab.\n\n🔶 ZELLE PAYMENT DETAILS:\n• Send to: ${zelleEmail}\n• Amount: $${amount}\n• Memo: ${memo}\n\nAfter signing in, go to "Send Money" or "Zelle" to make the payment.\nThen check the "Paid" box in the dashboard.`);
            }, 500);
        }
    }
}

// Create global venmo manager instance
window.venmoManager = new VenmoManager();
