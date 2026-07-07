package LibraryTypes {
	part def Rod {
		attribute length : ISQ::LengthValue;
		attribute mass : ISQ::MassValue;
	}
	part def Assembly {
		part rod : Rod;
	}
}
