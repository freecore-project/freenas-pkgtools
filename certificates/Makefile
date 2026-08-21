.include <bsd.own.mk>

FILESDIR= ${PREFIX}/share/certs

FILES=	FreeCORE-Production.pem \
	FreeCORE-Nightlies.pem \
	FreeCORE-15.0-Nightlies.pem \
	FreeCORE-15.0-STABLE.pem \
	freecore-update-ca.pem

beforeinstall:
	${INSTALL} -d ${DESTDIR}${FILESDIR}

.include <bsd.lib.mk>
